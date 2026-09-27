"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi } from "../../hooks/useApi";
import { TranscriptionPanel } from "../clinical/TranscriptionPanel";
import { CaseMedicineTrustPanel } from "../clinical/CaseMedicineTrustPanel";
import { describePriceCheck, PriceBasis, PriceCheck } from "../../lib/dawacheck";
import { TONE_CLASS } from "../../lib/labels";

// --- API Response Type (matching backend MedicineBenchmark schema) ---
interface MedicineBenchmarkResponse extends PriceCheck {
  brand_name: string;
  generic_substitute_available: boolean;
  generic_substitute_store_info: string;
  /** Provenance — the reference list is a curated subset of NPPA Schedule-I. */
  data_source: string;
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
    <div className="card">
      <div style={{ marginBottom: "1.5rem" }}>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </div>

      {/* ADR-011: uncertain prescription readings go to human readers, never silently into a medication fact */}
      {caseId && (
        <>
          <CaseMedicineTrustPanel caseId={caseId} caseToken={caseToken} refreshKey={caseRefresh} onChanged={bumpCase} />
          <TranscriptionPanel caseId={caseId} caseToken={caseToken} refreshKey={caseRefresh} onChanged={bumpCase} />
          <h3 style={{ marginBottom: "0.75rem" }}>Check any medicine by name</h3>
        </>
      )}

      {/* Search Form */}
      <div
        style={{
          display: "flex",
          gap: "0.75rem",
          marginBottom: "1.5rem",
          flexWrap: "wrap",
        }}
      >
        <input
          type="text"
          className="input-field"
          style={{ flex: 2, minWidth: "200px" }}
          placeholder={t.searchPlaceholder}
          value={brandName}
          onChange={(e) => setBrandName(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <input
          type="number"
          className="input-field"
          style={{ flex: 1, minWidth: "120px" }}
          placeholder="Amount paid (₹)"
          aria-label="Amount paid in rupees"
          step="0.01"
          min="0"
          value={mrp}
          onChange={(e) => setMrp(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <select
          className="input-field"
          style={{ flex: 1.4, minWidth: "190px" }}
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
        {needsCount && (
          <input
            type="number"
            className="input-field"
            style={{ flex: 1, minWidth: "140px" }}
            placeholder={basisOption?.needs === "pack" ? "Units in it (e.g. 15)" : "Number of units"}
            aria-label={basisOption?.needs === "pack" ? "Number of tablets or capsules in one strip or pack" : "Number of units the amount covers"}
            step="1"
            min="1"
            value={count}
            onChange={(e) => setCount(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        )}
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleSearch}
          disabled={api.loading || !formReady}
        >
          {api.loading ? "Checking..." : `🔍 ${t.searchBtn}`}
        </button>
      </div>

      {/* Error State */}
      {api.error && (
        <div
          style={{
            padding: "1rem",
            marginBottom: "1.5rem",
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid var(--status-danger)",
            borderRadius: "var(--radius-md)",
            color: "#fca5a5",
            fontSize: "0.9rem",
          }}
        >
          ⚠️ {api.error}
        </div>
      )}

      {/* Real Result */}
      {result && price && (
        <div style={{ marginBottom: "1.5rem" }}>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>{t.brandName}</th>
                  <th>{t.genericName}</th>
                  <th>{t.mrp}</th>
                  <th>{t.nppaCeiling}</th>
                  <th>{t.complianceCol}</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ fontWeight: 600 }}>{result.brand_name}</td>
                  <td style={{ color: "var(--text-secondary)" }}>{result.active_ingredient}</td>
                  <td>{price.billed}</td>
                  <td style={{ color: "var(--brand-cyan)", fontWeight: 600 }}>{price.ceiling}</td>
                  <td>
                    <span className={TONE_CLASS[price.tone]}>{price.badge}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          {price.reason && (
            <div role="status" style={{ marginTop: "0.75rem", fontSize: "0.85rem", color: "var(--status-warning)" }}>
              {price.reason}
            </div>
          )}
          {result.match_method === "fuzzy_phonetic" && (
            <div style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "var(--status-warning)" }}>
              Matched by spelling similarity to “{result.active_ingredient}” — check this is the same medicine.
            </div>
          )}

          {/* Generic Substitute Info */}
          {result.generic_substitute_available && (
            <div
              style={{
                marginTop: "1rem",
                padding: "0.85rem 1rem",
                backgroundColor: "rgba(16, 185, 129, 0.08)",
                borderRadius: "var(--radius-md)",
                fontSize: "0.85rem",
                color: "var(--brand-emerald)",
              }}
            >
              💊 <strong>Generic Alternative:</strong> {result.generic_substitute_store_info}
            </div>
          )}

          {/* Dataset Provenance Disclosure */}
          <div
            style={{
              marginTop: "0.75rem",
              padding: "0.65rem 1rem",
              fontSize: "0.78rem",
              color: "var(--status-warning)",
            }}
          >
            ⓘ {t.dataSourceNotice.replace("{count}", String(result.reference_entry_count))}
          </div>
        </div>
      )}

      {!result && !api.loading && (
        <div
          style={{
            padding: "0.65rem 0.85rem",
            marginBottom: "1rem",
            border: "1px dashed var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            fontSize: "0.85rem",
            color: "var(--text-secondary)",
          }}
        >
          NPPA ceiling prices are <strong>per tablet, capsule or vial</strong>. Tell us what your amount paid for — one
          unit, a strip, a pack, or several units — and DawaCheck converts it to a price per unit before comparing. If the
          number of units is not known, it says so instead of guessing.
        </div>
      )}

      <div
        style={{
          marginTop: "1.5rem",
          padding: "0.85rem 1rem",
          backgroundColor: "rgba(6, 182, 212, 0.08)",
          borderRadius: "var(--radius-md)",
          fontSize: "0.825rem",
          color: "var(--brand-cyan)",
        }}
      >
        💡 <strong>DPCO 2013 Provision:</strong> Charging above the notified NPPA ceiling price is an offence under the Essential Commodities Act, 1955. Retail pharmacies must mandatorily display generic bio-equivalents.
      </div>

      <div style={{ marginTop: "1.5rem", borderTop: "1px solid var(--border-subtle, rgba(255,255,255,0.08))", paddingTop: "1.25rem" }}>
        <h3 style={{ marginBottom: "0.75rem" }}>{t.prescriptionTranslatorTitle}</h3>
        <textarea
          className="textarea-field"
          rows={2}
          style={{ width: "100%", marginBottom: "0.75rem" }}
          placeholder={t.prescriptionInputPlaceholder}
          value={instructionsText}
          onChange={(e) => setInstructionsText(e.target.value)}
        />
        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleTranslate}
          disabled={translateApi.loading || !instructionsText.trim()}
        >
          {t.translateBtn}
        </button>

        {translateApi.data && (
          <div style={{ marginTop: "1rem" }}>
            {translateApi.data.instructions.length === 0 ? (
              <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>—</p>
            ) : (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                {translateApi.data.instructions.map((instr, idx) => (
                  <span
                    key={idx}
                    className={`badge ${instr.recognized ? "badge-success" : "badge-danger"}`}
                    title={instr.recognized ? t.recognizedBadge : undefined}
                  >
                    {instr.token} {instr.recognized ? `→ ${instr.translated}` : "?"}
                  </span>
                ))}
              </div>
            )}
            {translateApi.data.unrecognized_tokens.length > 0 && (
              <p style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                ⓘ {t.unrecognizedNotice.replace("{tokens}", translateApi.data.unrecognized_tokens.join(", "))}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
