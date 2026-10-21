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
import { PriceBar } from "./dawacheck/PriceBar";

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
  { value: "PER_UNIT", label: "One tablet / capsule / vial", needs: "none" },
  { value: "PER_STRIP", label: "One strip", needs: "pack" },
  { value: "PER_PACK", label: "One pack / box / bottle", needs: "pack" },
  { value: "LINE_TOTAL", label: "Several units (a bill line total)", needs: "quantity" },
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
  const price = result ? describePriceCheck(result) : null;

  return (
    <div className="module-panel">
      <header className="module-head">
        <p className="lp-kicker">DawaCheck · NPPA ceiling prices</p>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
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
        <h3 id="dc-form-title">Check any medicine by name</h3>
        <p className="bn-fine">
          NPPA ceiling prices are <strong>per tablet, capsule or vial</strong>. Say what your amount paid for — one unit, a
          strip, a pack, or several units — and DawaCheck converts it to a price per unit before comparing. If the number of
          units is not known, it says so instead of guessing.
        </p>
        <div className="dc-form">
          <div className="ds-field dc-field-name">
            <label className="input-label" htmlFor="dc-name">
              Medicine name and strength
              <span className="ds-required">required</span>
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
            <label className="input-label" htmlFor="dc-amount">
              Amount paid (₹)
              <span className="ds-required">required</span>
            </label>
            <input
              id="dc-amount"
              type="number"
              inputMode="decimal"
              className="input-field"
              aria-label="Amount paid in rupees"
              step="0.01"
              min="0"
              value={mrp}
              onChange={(e) => setMrp(e.target.value)}
              onKeyDown={handleKeyDown}
            />
          </div>
          <div className="ds-field">
            <label className="input-label" htmlFor="dc-basis">
              The amount is for
              <span className="ds-required">required</span>
            </label>
            <select
              id="dc-basis"
              className="select-field"
              aria-label="What the amount paid is for"
              value={basis}
              onChange={(e) => {
                setBasis(e.target.value as PriceBasis | "");
                setCount("");
              }}
            >
              <option value="">The amount is for…</option>
              {BASIS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          {needsCount && (
            <div className="ds-field">
              <label className="input-label" htmlFor="dc-count">
                {basisOption?.needs === "pack" ? "Units in it" : "Number of units"}
                <span className="ds-required">required</span>
              </label>
              <input
                id="dc-count"
                type="number"
                inputMode="numeric"
                className="input-field"
                placeholder={basisOption?.needs === "pack" ? "e.g. 15" : "e.g. 10"}
                aria-label={basisOption?.needs === "pack" ? "Number of tablets or capsules in one strip or pack" : "Number of units the amount covers"}
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
                <span className="spinner" aria-hidden="true" />
                Checking…
              </>
            ) : (
              t.searchBtn
            )}
          </button>
          {!formReady && <span className="ds-hint">Enter the name, the amount, and what the amount was for.</span>}
        </div>

        {/* Error State */}
        {api.error && (
          <StatePanel kind="error" onRetry={handleSearch}>
            Could not check the price: {api.error}
          </StatePanel>
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
            <p className="bn-notice is-warning">
              Matched by spelling similarity to “{result.active_ingredient}” — check this is the same medicine.
            </p>
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
              <strong>Generic alternative (from DawaCheck&apos;s reference data):</strong> {result.generic_substitute_store_info}
            </div>
          )}

          {/* Dataset Provenance Disclosure */}
          <p className="bn-fine">{t.dataSourceNotice.replace("{count}", String(result.reference_entry_count))}</p>
        </section>
      )}

      {/* law_library.json lists DPCO 2013 Para 14(1) as not verified against a primary source. */}
      <p className="dc-legal">
        <strong>Legal basis:</strong> NPPA notifies these ceilings under the Drugs (Prices Control) Order, 2013. This project
        has not yet verified the Order&apos;s text against the Gazette, so it makes no claim here about what follows when a
        price is above the ceiling.
      </p>

      <section className="case-panel bn-card" aria-labelledby="dc-rx-title">
        <h3 id="dc-rx-title">{t.prescriptionTranslatorTitle}</h3>
        <p className="bn-fine">Turns dosing abbreviations such as “OD”, “TDS” or “SOS” into plain words. Anything it does not know is listed, not guessed.</p>
        <label className="sr-only" htmlFor="dc-rx">
          Prescription instructions
        </label>
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
            {translateApi.loading ? "Translating…" : t.translateBtn}
          </button>
        </div>
        {translateApi.error && <StatePanel kind="error">Could not translate: {translateApi.error}</StatePanel>}

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
                      {instr.recognized ? instr.translated : "not recognised"}
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
