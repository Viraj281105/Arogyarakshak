// Pure layout for the case evidence graph (GET /cases/{id}/graph). No library: the API's graph is
// a hub (the hospital stay) with spokes to each extracted entity, plus a few cross links
// (BILLED_AS, POSSIBLY_SAME_AS), so a radial layout shows it faithfully. Unit-tested.

export interface GraphNode {
  id: string;
  kind: string;
  label: string;
  attributes: Record<string, unknown>;
  aliases: string[];
  source_files: string[];
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  evidence: { kind: string; source_files: string[]; score: number | null; detail: string }[];
}

export interface CaseGraph {
  case_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: Record<string, number>;
  limitations: string[];
}

export interface Placed {
  node: GraphNode;
  x: number;
  y: number;
}

export const KIND_ORDER = ["hospital", "diagnosis", "procedure", "medicine", "billing_item"];

/**
 * Hub at the centre (the `hospital_stay` node, or the first node if the API ever sends none),
 * every other node on one ring, grouped by kind in KIND_ORDER (unknown kinds last). Only nodes the
 * API returned are placed; edges whose ends are missing are dropped by `drawableEdges`.
 */
export function radialLayout(nodes: readonly GraphNode[], size: number): Placed[] {
  if (nodes.length === 0) return [];
  const cx = size / 2;
  const cy = size / 2;
  const hub = nodes.find((n) => n.kind === "hospital_stay") ?? nodes[0];
  const rank = (k: string) => {
    const i = KIND_ORDER.indexOf(k);
    return i === -1 ? KIND_ORDER.length : i;
  };
  const ring = nodes.filter((n) => n !== hub).sort((a, b) => rank(a.kind) - rank(b.kind) || a.label.localeCompare(b.label));
  const r = size * 0.38;
  const placed: Placed[] = [{ node: hub, x: cx, y: cy }];
  ring.forEach((node, i) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / ring.length;
    placed.push({ node, x: round(cx + r * Math.cos(angle)), y: round(cy + r * Math.sin(angle)) });
  });
  return placed;
}

/** Edges whose two ends were both placed. */
export function drawableEdges(edges: readonly GraphEdge[], placed: readonly Placed[]): GraphEdge[] {
  const ids = new Set(placed.map((p) => p.node.id));
  return edges.filter((e) => ids.has(e.source) && ids.has(e.target));
}

/** Edges touching one node (for the details panel and highlighting). */
export function edgesOf(id: string, edges: readonly GraphEdge[]): GraphEdge[] {
  return edges.filter((e) => e.source === id || e.target === id);
}

export function truncate(label: string, max = 16): string {
  return label.length > max ? `${label.slice(0, max - 1)}…` : label;
}

const round = (n: number) => Math.round(n * 10) / 10;
