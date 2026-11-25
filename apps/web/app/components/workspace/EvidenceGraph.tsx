"use client";

import React, { useEffect, useMemo, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../ui/States";
import { ScientificGridBackground } from "../illustrations/Backgrounds";
import { EvidenceVerificationIllustration } from "../illustrations/Illustrations";
import { casePath, getCaseJson } from "../../lib/caseApi";
import { useLanguage } from "../../shell/ShellProvider";
import { useCase } from "./CaseProvider";
import { drawableEdges, edgesOf, radialLayout, truncate, type CaseGraph } from "./graphLayout";
import { caseCopy, type CaseCopy } from "./caseCopy";
import { graphCopy, type GraphCopy } from "./graphCopy";
import { fillCopy, humanizeKey } from "./workspaceFormat";
import { useT } from "../../i18n/useT";

type WsCopy = CaseCopy & GraphCopy;

const SIZE = 640;

/**
 * Evidence graph of the case (GET /cases/{id}/graph, #86): only the nodes and links the API
 * returned, each link with the evidence it came from. No clinical relation is drawn (the API
 * infers none). The SVG is a picture; the table below is the full, accessible equivalent, and
 * every node in the picture is also a button that opens its details.
 */
export function EvidenceGraph() {
  const tr = useT();
  const [lang] = useLanguage();
  const c = { ...caseCopy[lang], ...graphCopy[lang] };
  const cs = useCase();
  const ref = cs.ref;
  const [graph, setGraph] = useState<CaseGraph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [kindFilter, setKindFilter] = useState<string>("all");

  useEffect(() => {
    if (!ref) return;
    let cancelled = false;
    getCaseJson<CaseGraph>(ref, `${casePath(ref.id)}/graph`)
      .then((g) => {
        if (cancelled) return;
        setGraph(g);
        setError(null);
      })
      .catch((err: unknown) => !cancelled && setError(err instanceof Error ? err.message : String(err)));
    return () => {
      cancelled = true;
    };
  }, [ref, tick]);

  const placed = useMemo(() => radialLayout(graph?.nodes ?? [], SIZE), [graph]);
  const edges = useMemo(() => drawableEdges(graph?.edges ?? [], placed), [graph, placed]);
  const pos = useMemo(() => new Map(placed.map((p) => [p.node.id, p])), [placed]);
  const label = (id: string) => pos.get(id)?.node.label ?? id;
  const kindLabel = (k: string) => c.graph.kinds[k as keyof WsCopy["graph"]["kinds"]] ?? humanizeKey(k);
  const relLabel = (r: string) => c.graph.relations[r as keyof WsCopy["graph"]["relations"]] ?? r;
  const evLabel = (k: string) => c.graph.evidence[k as keyof WsCopy["graph"]["evidence"]] ?? k;
  const sel = selected ? pos.get(selected)?.node : undefined;
  const selEdges = selected ? edgesOf(selected, edges) : [];

  return (
    <section className="ws-section" aria-labelledby="ws-graph-title">
      <h2 id="ws-graph-title" className="ws-section-title">
        {c.graph.title}
      </h2>
      <p className="ws-section-lede">{c.graph.lede}</p>
      {error ? (
        <ErrorState
          title={c.graph.error}
          action={
            <button type="button" className="btn btn-secondary btn-compact" onClick={() => setTick((n) => n + 1)}>
              {c.common.retry}
            </button>
          }
        >
          <p>{error}</p>
        </ErrorState>
      ) : !graph ? (
        <LoadingState label={c.common.loading} minHeight="12rem" />
      ) : graph.nodes.length <= 1 ? (
        <div className="ws-empty-with-art">
          <EvidenceVerificationIllustration size={112} />
          <EmptyState title={c.graph.empty}>
            <p>{c.graph.emptyBody}</p>
          </EmptyState>
        </div>
      ) : (
        <>
          <div className="ws-graph-toolbar">
            <p className="ws-muted">{fillCopy(c.graph.stats, { nodes: graph.stats.nodes ?? graph.nodes.length, edges: graph.stats.edges ?? graph.edges.length })}</p>
            <div className="ws-filters" role="group" aria-label={c.graph.legend}>
              <button type="button" className="ws-chip" aria-pressed={kindFilter === "all"} onClick={() => setKindFilter("all")}>{tr("All")}</button>
              {[...new Set(graph.nodes.map((n) => n.kind))].map((k) => (
                <button key={k} type="button" className="ws-chip" aria-pressed={kindFilter === k} onClick={() => setKindFilter((cur) => (cur === k ? "all" : k))}>
                  {kindLabel(k)}
                </button>
              ))}
            </div>
          </div>
          <div className="ws-graph">
            <div className="ws-graph-canvas">
              <ScientificGridBackground intensity={0.4} />
              <svg
                viewBox={`0 0 ${SIZE} ${SIZE}`}
                role="group"
                aria-label={fillCopy(c.graph.svgLabel, { nodes: graph.nodes.length, edges: edges.length })}
                className="ws-graph-svg"
              >
                {edges.map((e, i) => {
                  const a = pos.get(e.source)!;
                  const b = pos.get(e.target)!;
                  const hot = selected !== null && (e.source === selected || e.target === selected);
                  const dimmed = kindFilter !== "all" && a.node.kind !== kindFilter && b.node.kind !== kindFilter;
                  return (
                    <line
                      key={`${e.source}-${e.target}-${e.relation}-${i}`}
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      className={`ws-graph-edge ws-graph-edge-${e.relation.toLowerCase()}${hot ? " is-hot" : ""}${dimmed ? " is-dim" : ""}`}
                    />
                  );
                })}
                {placed.map((p) => {
                  const dimmed = kindFilter !== "all" && p.node.kind !== kindFilter && p.node.kind !== "hospital_stay";
                  const shown = truncate(p.node.kind === "hospital_stay" ? kindLabel(p.node.kind) : p.node.label);
                  const name = `${kindLabel(p.node.kind)}: ${p.node.label}`;
                  return (
                    <g
                      key={p.node.id}
                      role="button"
                      tabIndex={0}
                      aria-pressed={selected === p.node.id}
                      aria-label={shown.endsWith("…") ? `${shown} ${name}` : name}
                      className={`ws-graph-node ws-graph-node-${p.node.kind}${selected === p.node.id ? " is-selected" : ""}${dimmed ? " is-dim" : ""}`}
                      transform={`translate(${p.x} ${p.y})`}
                      onClick={() => setSelected((s) => (s === p.node.id ? null : p.node.id))}
                      onKeyDown={(ev) => {
                        if (ev.key === "Enter" || ev.key === " ") {
                          ev.preventDefault();
                          setSelected((s) => (s === p.node.id ? null : p.node.id));
                        }
                      }}
                    >
                      <circle r={p.node.kind === "hospital_stay" ? 22 : 12} />
                      <text y={p.node.kind === "hospital_stay" ? 38 : 26} textAnchor="middle">
                        {shown}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
            <ul className="ws-graph-legend" aria-label={c.graph.legend}>
              {[...new Set(graph.nodes.map((n) => n.kind))].map((k) => (
                <li key={k}>
                  <span className={`ws-graph-swatch ws-graph-node-${k}`} aria-hidden="true" />
                  {kindLabel(k)}
                </li>
              ))}
            </ul>
          </div>

          {sel && (
            <div className="ws-graph-detail" role="region" aria-live="polite" aria-label={c.graph.detailsLabel}>
              <p className="ws-action-title">
                {kindLabel(sel.kind)}: {sel.label}
              </p>
              {sel.aliases.length > 0 && <p className="ws-muted">{fillCopy(c.graph.aliases, { names: sel.aliases.join(", ") })}</p>}
              {sel.source_files.length > 0 && <p className="ws-muted">{fillCopy(c.graph.sources, { files: sel.source_files.join(", ") })}</p>}
              <ul>
                {selEdges.map((e, i) => (
                  <li key={i}>
                    {relLabel(e.relation)}: {e.source === sel.id ? label(e.target) : label(e.source)} — {e.evidence.map((ev) => evLabel(ev.kind)).join(", ")}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <details className="ws-fields">
            <summary>{c.graph.tableSummary}</summary>
            <div className="ws-table-scroll" tabIndex={0} role="region" aria-label={c.graph.tableSummary}>
              <table className="ws-table">
                <caption className="ws-visually-hidden">{c.graph.tableSummary}</caption>
                <thead>
                  <tr>
                    <th scope="col">{c.graph.colFrom}</th>
                    <th scope="col">{c.graph.colRelation}</th>
                    <th scope="col">{c.graph.colTo}</th>
                    <th scope="col">{c.graph.colEvidence}</th>
                  </tr>
                </thead>
                <tbody>
                  {edges.map((e, i) => (
                    <tr key={i}>
                      <td>{label(e.source)}</td>
                      <td>{relLabel(e.relation)}</td>
                      <td>{label(e.target)}</td>
                      <td>
                        {e.evidence
                          .map((ev) => `${evLabel(ev.kind)}${typeof ev.score === "number" ? ` (${Math.round(ev.score * 100)}%)` : ""}`)
                          .join(", ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>

          <details className="ws-fields">
            <summary>{c.graph.limitations}</summary>
            <ul lang="en">
              {graph.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </section>
  );
}
