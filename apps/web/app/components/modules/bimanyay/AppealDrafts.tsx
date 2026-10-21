"use client";

import React, { useState } from "react";
import { Language, translations } from "../../../translations";
import type { DisputeAuditResult } from "./types";

type Tier = "gro" | "bimabharosa" | "ombudsman";

/** The three statutory appeal drafts (insurer GRO, Bima Bharosa, Ombudsman) with copy. */
export function AppealDrafts({ result, currentLang }: { result: DisputeAuditResult; currentLang: Language }) {
  const t = translations[currentLang].modules.bimanyay;
  const [activeTab, setActiveTab] = useState<Tier>("gro");
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    let textToCopy = result.level_1_gro_appeal;
    if (activeTab === "bimabharosa") textToCopy = result.level_2_bimabharosa_text;
    if (activeTab === "ombudsman") textToCopy = result.level_3_ombudsman_grounds;

    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const tabs: { id: Tier; label: string }[] = [
    { id: "gro", label: t.groTab },
    { id: "bimabharosa", label: t.bimaBharosaTab },
    { id: "ombudsman", label: t.ombudsmanTab },
  ];

  return (
    <>
      {/* Appeals Tab Selector */}
      <div style={{ display: "flex", gap: "0.5rem", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.5rem", marginBottom: "1rem", overflowX: "auto" }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`btn ${activeTab === tab.id ? "btn-primary" : "btn-secondary"}`}
            style={{ fontSize: "0.85rem", padding: "0.5rem 1rem" }}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Appeal Content */}
      <div style={{ position: "relative", marginBottom: "1.5rem" }}>
        <button
          type="button"
          className="btn btn-secondary"
          style={{ position: "absolute", top: "0.75rem", right: "0.75rem", fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}
          onClick={handleCopy}
        >
          {copied ? `✓ ${t.copied}` : `📋 ${t.copyDraft}`}
        </button>

        <pre
          style={{
            background: "var(--bg-base)",
            padding: "1rem",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            fontSize: "0.85rem",
            fontFamily: "monospace",
            color: "var(--text-primary)",
            whiteSpace: "pre-wrap",
            lineHeight: 1.6,
            maxHeight: "340px",
            overflowY: "auto",
          }}
        >
          {activeTab === "gro" && result.level_1_gro_appeal}
          {activeTab === "bimabharosa" && result.level_2_bimabharosa_text}
          {activeTab === "ombudsman" && result.level_3_ombudsman_grounds}
        </pre>
      </div>
    </>
  );
}
