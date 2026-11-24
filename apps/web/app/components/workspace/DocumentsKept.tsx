"use client";

import React from "react";
import { ConfidenceIndicator, EvidenceBadge, StatusBadge } from "../ui/Badges";
import { EmptyState } from "../ui/States";
import type { CaseEntity } from "../../lib/caseApi";
import type { OverviewCopy } from "./overviewCopy";
import { formatRupees, humanizeKey } from "./workspaceFormat";

type WsCopy = OverviewCopy;

type Lang = "en" | "hi" | "mr";

const FIELD_ORDER = ["hospital", "diagnosis", "procedure", "medicine", "billing_item"];

function sourceOf(e: CaseEntity): string | null {
  const s = e.meta?.["source_file"];
  return typeof s === "string" && s ? s : null;
}

/** A confidence the API stored for this field, if any (OCR's lowest segment confidence today). */
export function storedConfidence(e: Pick<CaseEntity, "meta">): number | null {
  const meta = e.meta ?? {};
  const direct = meta["confidence"];
  if (typeof direct === "number" && Number.isFinite(direct)) return direct;
  const ocr = meta["ocr_uncertainty"];
  const min = ocr && typeof ocr === "object" ? (ocr as Record<string, unknown>)["min_ocr_confidence"] : null;
  return typeof min === "number" && Number.isFinite(min) ? min : null;
}

function warningsOf(e: CaseEntity): string[] {
  const w = e.meta?.["extraction_warnings"];
  return Array.isArray(w) ? w.filter((x): x is string => typeof x === "string") : [];
}

/**
 * What is actually kept from the documents (ADR-003): the details extracted from each one and a
 * redacted excerpt (names, contacts and IDs removed, first 1,000 characters). The original file
 * is never stored, so there is nothing to preview or download here.
 */
export function DocumentsKept({ c, lang, entities, emptyArt }: { c: WsCopy; lang: Lang; entities: CaseEntity[]; emptyArt?: React.ReactNode }) {
  const excerpts = entities.filter((e) => e.type === "document_text");
  const fields = entities.filter((e) => FIELD_ORDER.includes(e.type));
  const byType = FIELD_ORDER.map((type) => ({ type, items: fields.filter((e) => e.type === type) })).filter((g) => g.items.length > 0);

  return (
    <section className="ws-section" aria-labelledby="ws-docs-title">
      <h2 id="ws-docs-title" className="ws-section-title">
        {c.docs.title}
      </h2>
      <p className="ws-section-lede">{c.docs.lede}</p>

      {excerpts.length === 0 && fields.length === 0 ? (
        <div className="ws-empty-with-art">
          {emptyArt}
          <EmptyState title={c.docs.empty}>
            <p>{c.docs.emptyBody}</p>
          </EmptyState>
        </div>
      ) : (
        <>
          {excerpts.map((e) => (
            <article key={e.id} className="ws-doc">
              <header className="ws-doc-head">
                <h3 className="ws-subtitle">{sourceOf(e) ?? c.docs.unnamed}</h3>
                <EvidenceBadge state="unevaluated" size="sm" />
              </header>
              <p className="ws-muted">{c.docs.excerptNote}</p>
              {e.value ? <pre className="ws-excerpt">{e.value}</pre> : <p className="ws-muted">{c.docs.noExcerpt}</p>}
              {warningsOf(e).length > 0 && (
                <div className="ws-warning" role="note">
                  <p className="ws-action-title">{c.docs.warningsTitle}</p>
                  <ul>
                    {warningsOf(e).map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </article>
          ))}

          {byType.map((g) => (
            <details key={g.type} className="ws-fields" open={g.items.length <= 12}>
              <summary className="ws-fields-summary">
                <span>
                  {c.docs.types[g.type as keyof WsCopy["docs"]["types"]] ?? humanizeKey(g.type)} ({g.items.length})
                </span>
                <StatusBadge tone="neutral">Read automatically, not checked</StatusBadge>
              </summary>
              <div className="ws-table-scroll" tabIndex={0} role="region" aria-label={c.docs.types[g.type as keyof WsCopy["docs"]["types"]] ?? g.type}>
                <table className="ws-table">
                  <thead>
                    <tr>
                      <th scope="col">{c.docs.colName}</th>
                      <th scope="col">{c.docs.colValue}</th>
                      <th scope="col">{c.docs.colSource}</th>
                      <th scope="col">{c.docs.colConfidence}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {g.items.map((e) => {
                      const conf = storedConfidence(e);
                      return (
                        <tr key={e.id}>
                          <th scope="row">{e.name}</th>
                          <td className="code-tabular">{formatValue(e, lang)}</td>
                          <td>{sourceOf(e) ?? "—"}</td>
                          <td>{conf === null ? <span className="ws-muted">{c.docs.noConfidence}</span> : <ConfidenceIndicator value={conf} source={c.docs.ocrSource} label={c.docs.colConfidence} />}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </details>
          ))}
          <p className="ws-muted">{c.docs.notKept}</p>
        </>
      )}
    </section>
  );
}

/** Amounts (bill lines, medicine costs) are stored as text; show rupees only for a clean number. */
function formatValue(e: CaseEntity, lang: Lang): string {
  const v = e.value ?? "";
  if ((e.type === "billing_item" || e.type === "medicine" || e.type === "procedure") && /^\d+(\.\d+)?$/.test(v.trim())) {
    const n = Number(v);
    return n > 0 ? formatRupees(n, lang) : "—";
  }
  return v && v !== e.name ? v : "—";
}
