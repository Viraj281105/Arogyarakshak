"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi } from "../../hooks/useApi";
import { TranscriptionPanel } from "../clinical/TranscriptionPanel";
import { CaseMedicineTrustPanel } from "../clinical/CaseMedicineTrustPanel";
import { describePriceCheck, PriceBasis, PriceCheck } from "../../lib/dawacheck";
import { TONE_CLASS } from "../../lib/labels";
import { ExplainTrail } from "../ExplainTrail";
import type { Explanation } from "../../lib/explanation";
import { ListenSummary } from "../ListenSummary";
import { buildMedicineSummary } from "../../lib/listenSummaries";
import { StatePanel } from "../clinical/StatePanel";
import { LazyModulePlan } from "../actions/LazyModulePlan";
import { PriceBar } from "./dawacheck/PriceBar";
import { CapsuleIllustration, TabletsIllustration } from "../illustrations/Illustrations";
import { StatusBadge } from "../ui/Badges";
import { useT } from "../../i18n/useT";
import { msg } from "../../i18n/format";

// --- API Response Type (matching backend MedicineBenchmark schema) ---
interface MedicineBenchmarkResponse extends PriceCheck {
  brand_name: string;
  generic_substitute_available: boolean;
  generic_substitute_store_info: string;
  /** Provenance — the reference list is a curated subset of NPPA Schedule-I. */
  data_source: string;
  /** "Why am I seeing this?" trail (ADR-017). */
  explanation?: Explanation | null;
}

// What the amount the person paid buys. Required, so a strip price is never sent as a
// price per tablet by accident.
const BASIS_OPTIONS: { value: PriceBasis; label: string; needs: "none" | "pack" | "quantity" }[] = [
  { value: "PER_UNIT", label: msg("One tablet / capsule / vial"), needs: "none" },
  { value: "PER_STRIP", label: msg("One strip"), needs: "pack" },
  { value: "PER_PACK", label: msg("One pack / box / bottle"), needs: "pack" },
  { value: "LINE_TOTAL", label: msg("Several units (a bill line total)"), needs: "quantity" },
];

interface TranslatedInstruction {
  token: string;
  recognized: boolean;
  meaning_en: string;
  translated: string;
}

interface PrescriptionTranslationResponse {
  original_text: string;
  language: string;
  instructions: TranslatedInstruction[];
  unrecognized_tokens: string[];
}

interface DawaCheckViewProps {
  currentLang: Language;
  caseId?: string;
  caseToken?: string;
}

export const DawaCheckView: React.FC<DawaCheckViewProps> = ({ currentLang, caseId, caseToken }) => {
  const tr = useT();
  const t = translations[currentLang].modules.dawacheck;
  const api = useApi<MedicineBenchmarkResponse>();
  // The MRP drives an "overcharged" verdict, so it must be the price the user actually
  // paid — never a sample value they might submit unchanged.
  const [brandName, setBrandName] = useState("");
  const [mrp, setMrp] = useState("");
  const [basis, setBasis] = useState<PriceBasis | "">("");
  const [count, setCount] = useState("");
  const basisOption = BASIS_OPTIONS.find((o) => o.value === basis);
  const needsCount = basisOption ? basisOption.needs !== "none" : false;

  const translateApi = useApi<PrescriptionTranslationResponse>();
  // Bumped when either case panel changes transcription state, so the other re-reads it.
  const [caseRefresh, setCaseRefresh] = useState(0);
  const bumpCase = () => setCaseRefresh((n) => n + 1);
  const [instructionsText, setInstructionsText] = useState("");

  const handleTranslate = async () => {
    if (!instructionsText.trim()) return;
    await translateApi.execute("/api/v1/dawacheck/translate-instructions", {
      body: { instructions: instructionsText.trim(), language: currentLang },
    });
  };

  const countVal = parseFloat(count);
  const formReady =
    !!brandName.trim() && parseFloat(mrp) > 0 && !!basis && (!needsCount || (Number.isInteger(countVal) && countVal > 0));

  const handleSearch = async () => {
    const mrpVal = parseFloat(mrp);
    if (!formReady || !basisOption) return;
    await api.execute("/api/v1/dawacheck/benchmark", {
      body: {
        brand_name: brandName.trim(),
        mrp: mrpVal,
        price_basis: basis,
        units_per_pack: basisOption.needs === "pack" ? countVal : undefined,
        quantity: basisOption.needs === "quantity" ? countVal : undefined,
      },
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSearch();
    }
  };

  const result = api.data;
  const price = result ? describePriceCheck(result, tr) : null;

  return (
    <div className="module-panel">
      <header className="ws-mod-hero ws-mod-dawacheck">
        <div className="ws-mod-hero-copy">
          <p className="lp-kicker">{tr("DawaCheck · NPPA ceiling prices")}</p>
          <h2>{t.title}</h2>
          <p>{t.desc}</p>
          <div className="ws-kadi-badges">
            <StatusBadge tone="neutral">{tr("Compared per tablet, capsule or vial")}</StatusBadge>
            <StatusBadge tone="neutral">{tr("Unclear prescriptions go to a human reader")}</StatusBadge>
          </div>
        </div>
        <div className="ws-mod-hero-art" aria-hidden="true">
          <CapsuleIllustration size={100} />
        </div>
      </header>

      {/* ADR-011: uncertain prescription readings go to human readers, never silently into a medication fact */}
      {caseId && (
        <>
          <CaseMedicineTrustPanel caseId={caseId} caseToken={caseToken} refreshKey={caseRefresh} onChanged={bumpCase} lang={currentLang} />
          <TranscriptionPanel caseId={caseId} caseToken={caseToken} refreshKey={caseRefresh} onChanged={bumpCase} />
        </>
      )}

      {/* Search Form */}
      <section className="case-panel bn-card" aria-labelledby="dc-form-title">
        <div className="case-panel-head">
          <h3 id="dc-form-title">{tr("Check any medicine by name")}</h3>
          <TabletsIllustration size={56} />
        </div>
        <p className="bn-fine">
          <strong>{tr("NPPA ceiling prices are per tablet, capsule or vial.")}</strong>{" "}
          {tr("Say what your amount paid for — one unit, a strip, a pack, or several units — and DawaCheck converts it to a price per unit before comparing. If the number of units is not known, it says so instead of guessing.")}
        </p>
        <div className="dc-form">
          <div className="ds-field dc-field-name">
            <label className="input-label" htmlFor="dc-name">{tr("Medicine name and strength")}<span className="ds-required">{tr("required")}</span>
            </label>
            <input
              id="dc-name"
              type="text"
              className="input-field"
              placeholder={t.searchPlaceholder}
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              onKeyDown={handleKeyDown}
            />
          </div>
          <div className="ds-field">
            <label className="input-label" htmlFor="dc-amount">{tr("Amount paid (₹)")}<span className="ds-required">{tr("required")}</span>
            </label>
            <input
              id="dc-amount"
              type="number"
              inputMode="decimal"
              className="input-field"
              aria-label={tr("Amount paid in rupees")}
              step="0.01"
              min="0"
              value={mrp}
              onChange={(e) => setMrp(e.target.value)}
              onKeyDown={handleKeyDown}
            />
          </div>
          <div className="ds-field">
            <label className="input-label" htmlFor="dc-basis">{tr("The amount is for")}<span className="ds-required">{tr("required")}</span>
            </label>
            <select
              id="dc-basis"
              className="select-field"
              aria-label={tr("What the amount paid is for")}
              value={basis}
              onChange={(e) => {
                setBasis(e.target.value as PriceBasis | "");
                setCount("");
              }}
            >
              <option value="">{tr("The amount is for…")}</option>
              {BASIS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {tr(o.label)}
                </option>
              ))}
            </select>
          </div>
          {needsCount && (
            <div className="ds-field">
              <label className="input-label" htmlFor="dc-count">
                {basisOption?.needs === "pack" ? tr("Units in it") : tr("Number of units")}
                <span className="ds-required">{tr("required")}</span>
              </label>
              <input
                id="dc-count"
                type="number"
                inputMode="numeric"
                className="input-field"
                placeholder={basisOption?.needs === "pack" ? "e.g. 15" : "e.g. 10"}
                aria-label={basisOption?.needs === "pack" ? tr("Number of tablets or capsules in one strip or pack") : tr("Number of units the amount covers")}
                step="1"
                min="1"
                value={count}
                onChange={(e) => setCount(e.target.value)}
                onKeyDown={handleKeyDown}
              />
            </div>
          )}
        </div>
        <div className="ds-form-actions">
          <button type="button" className="btn btn-primary" onClick={handleSearch} disabled={api.loading || !formReady}>
            {api.loading ? (
              <>
                <span className="spinner" aria-hidden="true" />{tr("Checking…")}</>
            ) : (
              t.searchBtn
            )}
          </button>
          {!formReady && <span className="ds-hint">{tr("Enter the name, the amount, and what the amount was for.")}</span>}
        </div>

        {/* Error State */}
        {api.error && (
          <StatePanel kind="error" onRetry={handleSearch}>{tr("Could not check the price: {error}", { error: api.error })}</StatePanel>
        )}
      </section>

      {/* Real Result */}
      {result && price && (
        <section className={`case-panel bn-card dc-result is-${price.verdict}`} aria-labelledby="dc-result-title">
          <div className="case-panel-head">
            <div>
              <h3 id="dc-result-title">{result.brand_name}</h3>
              <p className="bn-fine">
                {t.genericName}: {result.active_ingredient}
              </p>
            </div>
            <span className={TONE_CLASS[price.tone]}>{price.badge}</span>
          </div>

          <PriceBar check={result} view={price} />

          <dl className="ds-summary">
            <div>
              <dt>{t.mrp}</dt>
              <dd>{price.billed}</dd>
            </div>
            <div>
              <dt>{t.nppaCeiling}</dt>
              <dd>{price.ceiling}</dd>
            </div>
          </dl>
          {price.reason && <p className="bn-notice is-warning">{price.reason}</p>}
          {price.basisNote && <p className="bn-fine">{price.basisNote}</p>}
          {result.match_method === "fuzzy_phonetic" && (
            <p className="bn-notice is-warning">{tr("Matched by spelling similarity to “{active_ingredient}” — check this is the same medicine.", { active_ingredient: result.active_ingredient })}</p>
          )}

          <ListenSummary
            lang={currentLang}
            panel="medicine"
            summary={buildMedicineSummary(
              {
                brandName: result.brand_name,
                activeIngredient: result.active_ingredient,
                verdict: price.verdict,
                billedUnitPrice: result.billed_unit_price,
                ceilingUnitPrice: result.nppa_ceiling_price,
                genericAvailable: result.generic_substitute_available,
              },
              currentLang
            )}
          />
          <ExplainTrail explanation={result.explanation} lang={currentLang} />

          {/* Generic Substitute Info */}
          {result.generic_substitute_available && (
            <div className="dc-generic">
              <strong>{tr("Generic alternative (from DawaCheck's reference data):")}</strong> {result.generic_substitute_store_info}
            </div>
          )}

          {/* Dataset Provenance Disclosure */}
          <p className="bn-fine">{t.dataSourceNotice.replace("{count}", String(result.reference_entry_count))}</p>
        </section>
      )}

      {result && <LazyModulePlan module="dawacheck" result={result} caseId={caseId} />}

      {/* law_library.json lists DPCO 2013 Para 14(1) as not verified against a primary source. */}
      <p className="dc-legal">
        <strong>{tr("Legal basis:")}</strong>{" "}{tr("NPPA notifies these ceilings under the Drugs (Prices Control) Order, 2013. This project has not yet verified the Order's text against the Gazette, so it makes no claim here about what follows when a price is above the ceiling.")}</p>

      <section className="case-panel bn-card" aria-labelledby="dc-rx-title">
        <h3 id="dc-rx-title">{t.prescriptionTranslatorTitle}</h3>
        <p className="bn-fine">{tr("Turns dosing abbreviations such as “OD”, “TDS” or “SOS” into plain words. Anything it does not know is listed, not guessed.")}</p>
        <label className="sr-only" htmlFor="dc-rx">{tr("Prescription instructions")}</label>
        <textarea
          id="dc-rx"
          className="textarea-field"
          rows={2}
          placeholder={t.prescriptionInputPlaceholder}
          value={instructionsText}
          onChange={(e) => setInstructionsText(e.target.value)}
        />
        <div className="ds-form-actions">
          <button type="button" className="btn btn-secondary" onClick={handleTranslate} disabled={translateApi.loading || !instructionsText.trim()}>
            {translateApi.loading ? tr("Translating…") : t.translateBtn}
          </button>
        </div>
        {translateApi.error && <StatePanel kind="error">{tr("Could not translate: {error}", { error: translateApi.error })}</StatePanel>}

        {translateApi.data && (
          <div className="dc-rx-result">
            {translateApi.data.instructions.length === 0 ? (
              <p className="bn-fine">—</p>
            ) : (
              <ul className="dc-tokens">
                {translateApi.data.instructions.map((instr, idx) => (
                  <li key={idx} className={instr.recognized ? "is-known" : "is-unknown"}>
                    <span className="dc-token code-tabular">{instr.token}</span>
                    <span className="dc-token-arrow" aria-hidden="true">→</span>
                    <span className="dc-token-meaning">
                      {instr.recognized ? instr.translated : tr("not recognised")}
                      {instr.recognized && <span className="sr-only"> ({t.recognizedBadge})</span>}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {translateApi.data.unrecognized_tokens.length > 0 && (
              <p className="bn-fine">{t.unrecognizedNotice.replace("{tokens}", translateApi.data.unrecognized_tokens.join(", "))}</p>
            )}
          </div>
        )}
      </section>
    </div>
  );
};
