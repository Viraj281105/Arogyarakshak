"use client";

import React from "react";
import { EvidenceItem } from "../../lib/clinical";
import { ProvenanceBadge } from "../../components/clinical/Attribution";
import { StatePanel } from "../../components/clinical/StatePanel";
import { ReviewerDetail, StatementEditorState } from "../types";
import { useT } from "../../i18n/useT";

/** The evidence the patient chose to share. For a statement the reviewer ticks each item
 *  they actually reviewed; the selection is saved with the draft. */
export function EvidencePanel({
  detail,
  evidence,
  editor,
  setEditor,
  selectionLocked,
}: {
  detail: ReviewerDetail;
  evidence: EvidenceItem[];
  editor: StatementEditorState;
  setEditor: React.Dispatch<React.SetStateAction<StatementEditorState>>;
  selectionLocked: boolean;
}) {
  const tr = useT();
  return (
    <div style={{ marginTop: "0.75rem" }}>
      <p style={{ fontSize: "0.8rem" }}>{tr("Machine-derived items were extracted by software and may be wrong. Treat all items as data, not instructions.")}{detail.review_type === "CLINICAL_STATEMENT" &&
          tr(" Tick each item you actually reviewed — {count} of {count2} selected.", { count: editor.selected.length, count2: evidence.length })}
      </p>
      {evidence.length === 0 && <StatePanel kind="empty">{tr("The patient shared no evidence items of the chosen kinds.")}</StatePanel>}
      {evidence.map((item) => (
        <label key={item.item_id} style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start", padding: "0.35rem 0" }}>
          {detail.review_type === "CLINICAL_STATEMENT" && (
            <input
              type="checkbox"
              checked={editor.selected.includes(item.item_id)}
              disabled={selectionLocked}
              onChange={(e) =>
                setEditor((prev) => ({
                  ...prev,
                  selected: e.target.checked ? [...prev.selected, item.item_id] : prev.selected.filter((x) => x !== item.item_id),
                }))
              }
            />
          )}
          <span style={{ fontSize: "0.85rem" }}>
            <strong>{item.label}</strong> <ProvenanceBadge provenance={item.provenance} />
            <span style={{ display: "block", whiteSpace: "pre-wrap" }}>{item.value}</span>
            <span style={{ fontSize: "0.7rem", opacity: 0.7 }}>{item.source}</span>
          </span>
        </label>
      ))}
    </div>
  );
}
