"use client";

import React, { useState } from "react";
import { Language, translations } from "../../../translations";
import type { DisputeAuditResult } from "./types";

type Tier = "gro" | "bimabharosa" | "ombudsman";

const WHO: Record<Tier, string> = {
  gro: "Send first, to the insurer's Grievance Redressal Officer.",
  bimabharosa: "If the insurer does not resolve it, register this on IRDAI's Bima Bharosa portal.",
  ombudsman: "If it is still unresolved, use this statement for the Insurance Ombudsman complaint.",
};

/** The three statutory appeal drafts (insurer GRO, Bima Bharosa, Ombudsman) with copy. */
export function AppealDrafts({ result, currentLang }: { result: DisputeAuditResult; currentLang: Language }) {
  const t = translations[currentLang].modules.bimanyay;
  const [activeTab, setActiveTab] = useState<Tier>("gro");
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);

  const draftFor = (tier: Tier) =>
    tier === "gro" ? result.level_1_gro_appeal : tier === "bimabharosa" ? result.level_2_bimabharosa_text : result.level_3_ombudsman_grounds;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(draftFor(activeTab));
      setCopyFailed(false);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopyFailed(true);
    }
  };

  const tabs: { id: Tier; label: string }[] = [
    { id: "gro", label: t.groTab },
    { id: "bimabharosa", label: t.bimaBharosaTab },
    { id: "ombudsman", label: t.ombudsmanTab },
  ];

  return (
    <section className="case-panel bn-card" aria-labelledby="bm-drafts-title">
      <div className="case-panel-head">
        <h3 id="bm-drafts-title">Appeal drafts, one per escalation step</h3>
      </div>
      <p className="bn-fine">Drafted by software from what you entered. Review and edit before sending; this is not legal advice.</p>

      <div className="bm-tiers" role="tablist" aria-label="Escalation step">
        {tabs.map((tab, i) => (
          <button
            key={tab.id}
            id={`bm-tab-${tab.id}`}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls="bm-draft-panel"
            className={`bm-tier ${activeTab === tab.id ? "is-active" : ""}`}
            onClick={() => {
              setActiveTab(tab.id);
              setCopied(false);
            }}
          >
            <span className="bm-tier-num" aria-hidden="true">
              {i + 1}
            </span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      <div id="bm-draft-panel" role="tabpanel" aria-labelledby={`bm-tab-${activeTab}`} className="bm-draft">
        <p className="bm-draft-who">{WHO[activeTab]}</p>
        <article className="bn-letter">
          <pre>
            {activeTab === "gro" && result.level_1_gro_appeal}
            {activeTab === "bimabharosa" && result.level_2_bimabharosa_text}
            {activeTab === "ombudsman" && result.level_3_ombudsman_grounds}
          </pre>
        </article>
        <div className="bn-actions-row">
          <button type="button" className="btn btn-secondary" onClick={() => void handleCopy()}>
            <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
              <path d="M8 8h11v12H8zM5 16V4h11" />
            </svg>
            {copied ? t.copied : t.copyDraft}
          </button>
          {copyFailed && <span className="ds-hint">Could not copy — select the text and copy it instead.</span>}
        </div>
      </div>
    </section>
  );
}
