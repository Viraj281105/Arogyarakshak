// Ambient scientific backgrounds. Decorative only (aria-hidden), absolutely positioned behind content,
// CSS-animated (illustrations.css), stopped by prefers-reduced-motion and data-motion="reduce".
// Deterministic geometry (a fixed seed), so server and client markup are identical. They never carry
// text, figures or patient data. Place inside a positioned parent:
//   <section style={{ position: "relative" }}><MolecularNetworkBackground />...</section>

type BgProps = { className?: string; /** 0..1 visual strength; defaults per background. */ intensity?: number };

function wrap(name: string, { className, intensity }: BgProps, defaultIntensity: number) {
  return {
    className: ["illo-bg", `illo-bg-${name}`, className].filter(Boolean).join(" "),
    style: { ["--illo-bg-intensity" as string]: String(intensity ?? defaultIntensity) },
    "aria-hidden": true as const,
  };
}

/** Small deterministic PRNG (mulberry32) for stable layouts. */
function prng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const r1 = (n: number) => Math.round(n * 10) / 10;

const NETWORK = (() => {
  const rand = prng(20261124);
  const nodes = Array.from({ length: 44 }, (_, i) => ({
    id: i,
    x: r1(4 + rand() * 192),
    y: r1(5 + rand() * 90),
    r: r1(0.45 + rand() * 0.7),
    hub: rand() > 0.82,
  }));
  const edges: Array<[number, number]> = [];
  for (const a of nodes) {
    const near = nodes
      .filter((b) => b.id !== a.id)
      .map((b) => ({ b, d: Math.hypot(a.x - b.x, (a.y - b.y) * 0.6) }))
      .sort((p, q) => p.d - q.d)
      .slice(0, 2);
    for (const { b, d } of near) if (d < 30 && a.id < b.id) edges.push([a.id, b.id]);
  }
  return { nodes, edges };
})();

/** Molecular network: nodes and bonds drifting slowly; a few bonds pulse. */
export function MolecularNetworkBackground(props: BgProps) {
  const { nodes, edges } = NETWORK;
  return (
    <div {...wrap("network", props, 0.55)}>
      <svg viewBox="0 0 200 100" preserveAspectRatio="xMidYMid slice">
        <g className="illo-bg-drift">
          {edges.map(([a, b], i) => (
            <line
              key={`${a}-${b}`}
              className={i % 5 === 0 ? "illo-bg-bond illo-bg-bond-live" : "illo-bg-bond"}
              x1={nodes[a].x}
              y1={nodes[a].y}
              x2={nodes[b].x}
              y2={nodes[b].y}
              pathLength={100}
              style={{ animationDelay: `${(i % 7) * 0.9}s` }}
            />
          ))}
          {nodes.map((n) => (
            <circle key={n.id} className={n.hub ? "illo-bg-node illo-bg-hub" : "illo-bg-node"} cx={n.x} cy={n.y} r={n.hub ? n.r * 1.6 : n.r} />
          ))}
        </g>
      </svg>
    </div>
  );
}

/** Scientific grid: fine graph-paper grid with a slow light sweep; masked to fade at the edges. */
export function ScientificGridBackground(props: BgProps) {
  return (
    <div {...wrap("grid", props, 0.6)}>
      <div className="illo-bg-grid-lines" />
      <div className="illo-bg-grid-sweep" />
    </div>
  );
}

const LEAVES = (() => {
  const rand = prng(7);
  return Array.from({ length: 15 }, (_, i) => ({
    x: r1(8 + (i % 5) * 40 + rand() * 18),
    y: r1(12 + Math.floor(i / 5) * 32 + rand() * 12),
    rot: Math.round(rand() * 360),
    s: r1(0.55 + rand() * 0.5),
  }));
})();

/** Botanical geometry: outlined leaves with venation, rotating very slowly. */
export function BotanicalGeometryBackground(props: BgProps) {
  return (
    <div {...wrap("botanical", props, 0.5)}>
      <svg viewBox="0 0 200 100" preserveAspectRatio="xMidYMid slice">
        {LEAVES.map((l, i) => (
          <g key={i} transform={`translate(${l.x} ${l.y}) rotate(${l.rot}) scale(${l.s})`}>
            <g className="illo-bg-leaf" style={{ animationDelay: `${i * -2.3}s` }}>
              <path d="M0 9 C-6 6 -8 -1 -6 -9 C-1 -7 3 -1 0 9 Z" />
              <path d="M0 9 C-2 3 -3.5 -3 -6 -9 M-1.4 4 L-4 2.6 M-2.6 -0.4 L-5 -2" />
            </g>
          </g>
        ))}
        <circle className="illo-bg-ring" cx="100" cy="50" r="40" />
        <circle className="illo-bg-ring" cx="100" cy="50" r="26" />
      </svg>
    </div>
  );
}

/** Medical waveform: a calm ECG-like trace scrolling horizontally (two copies for a seamless loop). */
export function MedicalWaveformBackground(props: BgProps) {
  const beat = "h14 l3 -3 l3 3 h4 l3 -16 l4 30 l3 -20 l3 6 h10 l4 -4 l4 4 h12";
  const line = `M0 50 ${Array.from({ length: 4 }, () => beat).join(" ")}`;
  return (
    <div {...wrap("waveform", props, 0.6)}>
      <svg viewBox="0 0 400 100" preserveAspectRatio="none">
        <g className="illo-bg-wave-track">
          <path className="illo-bg-wave" d={line} />
          <path className="illo-bg-wave" d={line} transform="translate(280 0)" />
          <path className="illo-bg-wave" d={line} transform="translate(560 0)" />
        </g>
      </svg>
    </div>
  );
}

/** Document intelligence: stacked document outlines with text rows and a slow scanning beam. */
export function DocumentIntelligenceBackground(props: BgProps) {
  const docs = [
    { x: 10, y: 22, r: -6 },
    { x: 46, y: 12, r: 3 },
    { x: 84, y: 26, r: -2 },
    { x: 122, y: 14, r: 4 },
    { x: 160, y: 24, r: -4 },
  ];
  return (
    <div {...wrap("docs", props, 0.5)}>
      <svg viewBox="0 0 200 80" preserveAspectRatio="xMidYMid slice">
        {docs.map((d, i) => (
          <g key={i} transform={`translate(${d.x} ${d.y}) rotate(${d.r})`}>
            {/* Animated inner group: a CSS transform would replace the SVG transform attribute above. */}
            <g className="illo-bg-doc" style={{ animationDelay: `${i * -3}s` }}>
              <rect width="22" height="30" rx="1.2" />
              <path d="M3 5 H17 M3 9 H14 M3 13 H18 M3 17 H12 M3 21 H16" />
              <rect className="illo-bg-docbox" x="2" y="11.5" width="15" height="3" rx="0.6" />
            </g>
          </g>
        ))}
        <rect className="illo-bg-docbeam" x="0" y="0" width="200" height="1.2" />
      </svg>
    </div>
  );
}

export const BACKGROUNDS = {
  network: MolecularNetworkBackground,
  grid: ScientificGridBackground,
  botanical: BotanicalGeometryBackground,
  waveform: MedicalWaveformBackground,
  documents: DocumentIntelligenceBackground,
} as const;
