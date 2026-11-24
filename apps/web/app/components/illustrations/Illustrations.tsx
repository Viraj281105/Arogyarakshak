// ArogyaRakshak illustration library: "botanical-architectural line and wash" (docs/transformation/
// ILLUSTRATION_SYSTEM.md). Every illustration is a plain SVG on a 160 x 120 grid, coloured only through
// CSS variables (illustrations.css), so it follows the theme and ships no JavaScript: no hooks, no
// client directive, no randomness (server and client render the same markup).
//
// Rules: illustrations are decorative by default (aria-hidden) and never carry patient data, real
// figures or claims. Pass `title` only when the picture itself conveys meaning that the text does not.
// Animation hooks (classes on parts) are opt-in through `animate`; all of them stop under reduced motion.
import type { ReactNode } from "react";

export type IllustrationProps = {
  /** Width in px (height follows the 4:3 grid). Omit to fill the container width. */
  size?: number;
  /** Accessible name; when omitted the illustration is decorative (aria-hidden). */
  title?: string;
  /** Turn on the illustration's own motion (drawing, floating, scanning, pulse). */
  animate?: boolean;
  className?: string;
};

function Frame({ size, title, animate, className, name, children }: IllustrationProps & { name: string; children: ReactNode }) {
  const cls = ["illo", `illo-${name}`, animate ? "illo--animate" : "", className].filter(Boolean).join(" ");
  const a11y = title ? { role: "img", "aria-label": title } : { "aria-hidden": true as const, focusable: "false" as const };
  return (
    <svg viewBox="0 0 160 120" width={size} height={size ? (size * 3) / 4 : undefined} className={cls} {...a11y}>
      {title ? <title>{title}</title> : null}
      {children}
    </svg>
  );
}

/** Soft ground shadow shared by most illustrations. */
const Ground = ({ cx = 80, w = 56 }: { cx?: number; w?: number }) => (
  <ellipse className="illo-ground" cx={cx} cy={110} rx={w} ry={4.5} />
);

/* ------------------------------------------------------------------ Science */

export function AnatomyIllustration(p: IllustrationProps) {
  return (
    <Frame {...p} name="anatomy">
      <Ground w={40} />
      <circle className="illo-wash illo-line" cx={80} cy={20} r={11} />
      <path className="illo-wash illo-line" d="M58 40 C64 35.5 72 34 80 34 C88 34 96 35.5 102 40 C108 44.5 110 52 110 62 L107 106 H53 L50 62 C50 52 52 44.5 58 40 Z" />
      <path className="illo-accent-fill illo-line-thin" d="M73 49 C64.5 51.5 60.5 62 61.5 78 C62.2 87 70.5 87.5 74.5 80.5 L76.5 53 Z" />
      <path className="illo-accent-fill illo-line-thin" d="M87 49 C95.5 51.5 99.5 62 98.5 78 C97.8 87 89.5 87.5 85.5 80.5 L83.5 53 Z" />
      <path className="illo-line-thin illo-dash" d="M80 42 V102" />
      <path className="illo-heart illo-pulse" d="M83 66 C80.4 62.2 74.6 63.6 75.4 68.6 C76.2 73.4 83 77.6 83 77.6 C83 77.6 89.8 73.4 90.6 68.6 C91.4 63.6 85.6 62.2 83 66 Z" />
      <path className="illo-line-thin" d="M64 92 C70 95 90 95 96 92" />
    </Frame>
  );
}

function helix(phase: number) {
  const pts: string[] = [];
  for (let i = 0; i <= 48; i++) {
    const x = 18 + i * (124 / 48);
    const y = 60 + 28 * Math.sin((i / 48) * Math.PI * 3 + phase);
    pts.push(`${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`);
  }
  return pts.join(" ");
}

export function DnaIllustration(p: IllustrationProps) {
  const rungs = Array.from({ length: 16 }, (_, i) => {
    const t = (i + 0.5) / 16;
    const x = 18 + t * 124;
    const a = 60 + 28 * Math.sin(t * Math.PI * 3);
    const b = 60 + 28 * Math.sin(t * Math.PI * 3 + Math.PI);
    return { x: x.toFixed(2), a: a.toFixed(2), b: b.toFixed(2), alt: i % 2 === 0 };
  });
  return (
    <Frame {...p} name="dna">
      {rungs.map((r) => (
        <line key={r.x} className={r.alt ? "illo-rung" : "illo-rung illo-rung-alt"} x1={r.x} y1={r.a} x2={r.x} y2={r.b} />
      ))}
      <path className="illo-line illo-draw" pathLength={100} d={helix(0)} />
      <path className="illo-line-accent illo-draw illo-draw-late" pathLength={100} d={helix(Math.PI)} />
    </Frame>
  );
}

export function HeartbeatIllustration(p: IllustrationProps) {
  return (
    <Frame {...p} name="heartbeat">
      <rect className="illo-panel" x={10} y={22} width={140} height={76} rx={10} />
      <path className="illo-grid" d="M10 41 H150 M10 60 H150 M10 79 H150 M38 22 V98 M66 22 V98 M94 22 V98 M122 22 V98" />
      <path className="illo-signal-line illo-draw illo-trace" pathLength={100} d="M14 64 H46 L52 64 L57 58 L62 64 L68 64 L73 34 L80 90 L86 50 L91 64 H104 L110 58 L116 64 H146" />
      <path className="illo-heart illo-pulse" d="M136 34 C134 31 129.5 32 130 36 C130.6 39.6 136 43 136 43 C136 43 141.4 39.6 142 36 C142.5 32 138 31 136 34 Z" />
    </Frame>
  );
}

export function CellIllustration(p: IllustrationProps) {
  return (
    <Frame {...p} name="cell">
      <path className="illo-wash illo-line" d="M80 14 C112 12 146 30 146 60 C146 92 114 108 80 106 C44 104 14 90 14 58 C14 30 48 16 80 14 Z" />
      <path className="illo-line-thin illo-dash" d="M80 22 C107 21 137 35 137 60 C137 86 110 99 80 98 C50 97 23 85 23 58 C23 35 52 23 80 22 Z" />
      <circle className="illo-accent-fill illo-line" cx={84} cy={58} r={17} />
      <circle className="illo-line-thin illo-solid" cx={88} cy={54} r={5.5} />
      <g transform="rotate(-24 46 46)">
        <ellipse className="illo-signal-fill illo-line-thin illo-float" cx={46} cy={46} rx={11} ry={5.5} />
      </g>
      <path className="illo-line-thin" d="M38 48 C42 44 44 50 48 46 C51 43 53 47 55 44" />
      <g transform="rotate(18 116 82)">
        <ellipse className="illo-signal-fill illo-line-thin illo-float illo-float-late" cx={116} cy={82} rx={10} ry={5} />
      </g>
      <circle className="illo-dot" cx={52} cy={80} r={2.4} />
      <circle className="illo-dot" cx={60} cy={88} r={1.8} />
      <circle className="illo-dot" cx={118} cy={44} r={2.2} />
      <circle className="illo-dot" cx={108} cy={36} r={1.6} />
      <circle className="illo-dot" cx={70} cy={86} r={1.6} />
    </Frame>
  );
}

const HEX = [0, 1, 2, 3, 4, 5].map((i) => {
  const a = (Math.PI / 3) * i - Math.PI / 2;
  return [Math.round((70 + 20 * Math.cos(a)) * 100) / 100, Math.round((60 + 20 * Math.sin(a)) * 100) / 100] as const;
});

export function MoleculeIllustration(p: IllustrationProps) {
  const ring = HEX.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`).join(" ") + " Z";
  const branches: Array<[number, number, number, number]> = [
    [HEX[0][0], HEX[0][1], 70, 18],
    [HEX[1][0], HEX[1][1], 112, 36],
    [112, 36, 136, 24],
    [112, 36, 128, 60],
    [HEX[4][0], HEX[4][1], 28, 84],
    [HEX[3][0], HEX[3][1], 70, 104],
  ];
  return (
    <Frame {...p} name="molecule">
      <path className="illo-wash illo-line" d={ring} />
      <path className="illo-line-thin" d={HEX.map(([x, y]) => `M70 60 L${x.toFixed(2)} ${y.toFixed(2)}`).join(" ")} strokeOpacity={0.3} />
      {branches.map(([x1, y1, x2, y2], i) => (
        <line key={i} className="illo-line illo-draw" pathLength={100} x1={x1} y1={y1} x2={x2} y2={y2} />
      ))}
      {HEX.map(([x, y], i) => (
        <circle key={i} className="illo-atom" cx={x} cy={y} r={5} />
      ))}
      <circle className="illo-atom illo-atom-accent illo-float" cx={70} cy={18} r={7} />
      <circle className="illo-atom" cx={112} cy={36} r={6} />
      <circle className="illo-atom illo-atom-signal illo-float illo-float-late" cx={136} cy={24} r={6.5} />
      <circle className="illo-atom illo-atom-accent" cx={128} cy={60} r={5.5} />
      <circle className="illo-atom illo-atom-signal" cx={28} cy={84} r={6.5} />
      <circle className="illo-atom" cx={70} cy={104} r={5.5} />
    </Frame>
  );
}

/* ------------------------------------------------------------------ Medicines */

export function CapsuleIllustration(p: IllustrationProps) {
  return (
    <Frame {...p} name="capsule">
      <Ground w={46} />
      {/* The rotation sits on the outer group: a CSS animation transform would replace an SVG transform attribute on the same element. */}
      <g transform="rotate(-32 80 60)">
        <g className="illo-float">
          <path className="illo-wash illo-line" d="M80 42 H54 C44 42 36 50 36 60 C36 70 44 78 54 78 H80 Z" />
          <path className="illo-accent-strong illo-line" d="M80 42 H106 C116 42 124 50 124 60 C124 70 116 78 106 78 H80 Z" />
          <path className="illo-highlight" d="M48 51 C51 48 56 47 62 47" />
        </g>
      </g>
      <circle className="illo-dot" cx={34} cy={96} r={2.6} />
      <circle className="illo-dot" cx={44} cy={101} r={1.8} />
      <circle className="illo-dot" cx={124} cy={98} r={2.2} />
      <circle className="illo-dot" cx={132} cy={92} r={1.6} />
    </Frame>
  );
}

export function TabletsIllustration(p: IllustrationProps) {
  const cells = [0, 1, 2].flatMap((c) => [0, 1].map((r) => [92 + c * 18, 34 + r * 26] as const));
  return (
    <Frame {...p} name="tablets">
      <Ground w={60} />
      <rect className="illo-panel illo-line" x={82} y={22} width={64} height={66} rx={8} />
      {cells.map(([x, y], i) => (
        <circle key={i} className={i === 4 ? "illo-line-thin illo-empty" : "illo-wash illo-line-thin"} cx={x + 1} cy={y + 9} r={7} />
      ))}
      <g className="illo-float">
        <circle className="illo-surface illo-line" cx={42} cy={64} r={18} />
        <path className="illo-line-thin" d="M28 64 H56" />
      </g>
      <g className="illo-float illo-float-late">
        <ellipse className="illo-accent-fill illo-line" cx={58} cy={96} rx={14} ry={7} />
        <path className="illo-line-thin" d="M58 89.5 V102.5" />
      </g>
    </Frame>
  );
}

export function PrescriptionIllustration(p: IllustrationProps) {
  return (
    <Frame {...p} name="prescription">
      <Ground w={44} />
      <path className="illo-surface illo-line" d="M44 10 H106 L118 22 V106 H44 Z" />
      <path className="illo-line-thin illo-solid-light" d="M106 10 V22 H118" />
      <path className="illo-line illo-rx" d="M54 30 V50 M54 30 H62 C66.5 30 69 33 69 36 C69 39.5 66.5 42 62 42 H54 M61 42 L72 54 M72 44 L62 55" />
      <path className="illo-text" d="M80 32 H108 M80 40 H100" />
      <path className="illo-text" d="M54 66 H108 M54 75 H98 M54 84 H104" />
      <path className="illo-signal-line" d="M86 98 C90 92 94 102 98 96 C101 92 104 98 108 95" />
    </Frame>
  );
}

/* ------------------------------------------------------------------ Care */

export function HospitalIllustration(p: IllustrationProps) {
  const windows = [0, 1, 2].flatMap((r) => [0, 1, 2, 3].map((c) => [44 + c * 20, 52 + r * 16] as const));
  return (
    <Frame {...p} name="hospital">
      <Ground w={66} />
      <rect className="illo-wash illo-line" x={32} y={36} width={96} height={72} rx={3} />
      <rect className="illo-surface illo-line" x={60} y={14} width={40} height={30} rx={3} />
      <path className="illo-cross" d="M80 20 V38 M71 29 H89" />
      {windows.map(([x, y], i) => (
        <rect key={i} className="illo-window" x={x} y={y} width={12} height={8} rx={1.5} />
      ))}
      <path className="illo-surface illo-line" d="M70 108 V92 C70 88 74 85 80 85 C86 85 90 88 90 92 V108" />
      <path className="illo-line-thin" d="M18 108 H142" />
      <path className="illo-leaf" d="M20 108 C16 98 18 90 24 86 C28 94 26 102 20 108 Z" />
      <path className="illo-leaf" d="M140 108 C144 98 142 90 136 86 C132 94 134 102 140 108 Z" />
    </Frame>
  );
}

export function PatientIllustration(p: IllustrationProps) {
  return (
    <Frame {...p} name="patient">
      <Ground w={60} />
      <path className="illo-line" d="M22 70 V104 M138 82 V104 M22 90 H138" />
      <rect className="illo-surface illo-line" x={22} y={60} width={16} height={20} rx={4} />
      <circle className="illo-wash illo-line" cx={52} cy={64} r={9} />
      <path className="illo-accent-fill illo-line" d="M44 76 H122 C130 76 136 80 136 86 V90 H44 Z" />
      <path className="illo-line-thin" d="M66 80 C80 84 98 84 112 80" />
      <path className="illo-line-thin" d="M120 20 V58" />
      <path className="illo-surface illo-line" d="M112 20 H128 V36 C128 40 124 42 120 42 C116 42 112 40 112 36 Z" />
      <path className="illo-signal-line illo-draw" pathLength={100} d="M120 42 C120 50 112 54 104 54 C96 54 92 60 92 66" />
      <path className="illo-heart illo-pulse" d="M60 36 C58 33 53.5 34 54 38 C54.6 41.6 60 45 60 45 C60 45 65.4 41.6 66 38 C66.5 34 62 33 60 36 Z" />
    </Frame>
  );
}

/* ------------------------------------------------------------------ Documents and evidence */

export function MedicalRecordIllustration(p: IllustrationProps) {
  return (
    <Frame {...p} name="record">
      <Ground w={54} />
      <path className="illo-accent-fill illo-line" d="M26 30 H62 L70 22 H134 V104 H26 Z" />
      <rect className="illo-surface illo-line illo-float" x={38} y={36} width={84} height={62} rx={4} />
      <path className="illo-text" d="M48 48 H86 M48 56 H76" />
      <path className="illo-signal-line" d="M48 76 H62 L66 68 L71 84 L75 72 L78 76 H112" />
      <circle className="illo-wash illo-line-thin" cx={104} cy={52} r={8} />
      <path className="illo-cross-small" d="M104 48 V56 M100 52 H108" />
    </Frame>
  );
}

export function InsuranceShieldIllustration(p: IllustrationProps) {
  return (
    <Frame {...p} name="insurance">
      <Ground w={50} />
      <rect className="illo-surface illo-line" x={24} y={24} width={64} height={80} rx={4} transform="rotate(-6 56 64)" />
      <path className="illo-text" d="M34 40 H70 M34 48 H62 M34 56 H68" transform="rotate(-6 56 64)" />
      <g className="illo-float">
        <path className="illo-shield illo-line" d="M104 22 C112 26 120 28 128 29 V58 C128 76 118 88 104 95 C90 88 80 76 80 58 V29 C88 28 96 26 104 22 Z" />
        <path className="illo-check" d="M94 59 L101 66 L115 50" />
      </g>
      <path className="illo-leaf" d="M84 98 C78 92 78 84 82 78 C88 84 88 92 84 98 Z" />
    </Frame>
  );
}

export function DocumentScanIllustration(p: IllustrationProps) {
  return (
    <Frame {...p} name="scan">
      <Ground w={46} />
      <path className="illo-surface illo-line" d="M46 12 H102 L114 24 V106 H46 Z" />
      <path className="illo-line-thin illo-solid-light" d="M102 12 V24 H114" />
      <path className="illo-text" d="M56 32 H92 M56 42 H104 M56 52 H98 M56 62 H104 M56 72 H86 M56 82 H100 M56 92 H94" />
      <path className="illo-corner" d="M36 22 V12 H46 M124 22 V12 H114 M36 96 V106 H46 M124 96 V106 H114" />
      <g className="illo-scanbeam">
        <rect className="illo-beam-glow" x={34} y={44} width={92} height={14} />
        <path className="illo-beam" d="M34 51 H126" />
      </g>
    </Frame>
  );
}

export function OcrIllustration(p: IllustrationProps) {
  return (
    <Frame {...p} name="ocr">
      <path className="illo-surface illo-line" d="M10 16 H70 V104 H10 Z" />
      <path className="illo-text" d="M18 28 H58 M18 38 H50 M18 58 H60 M18 68 H46 M18 88 H56" />
      <rect className="illo-box illo-box-a" x={15} y={33} width={40} height={10} rx={2} />
      <rect className="illo-box illo-box-b" x={15} y={63} width={36} height={10} rx={2} />
      <rect className="illo-box illo-box-c" x={15} y={83} width={46} height={10} rx={2} />
      <path className="illo-line-thin illo-dash illo-flow" d="M76 60 H90" />
      <path className="illo-arrow" d="M88 56 L93 60 L88 64" />
      {[30, 56, 82].map((y, i) => (
        <g key={y} className={`illo-field illo-field-${i}`}>
          <rect className="illo-wash illo-line-thin" x={98} y={y - 8} width={54} height={20} rx={5} />
          <circle className={i === 1 ? "illo-dot-attention" : "illo-dot-verified"} cx={107} cy={y + 2} r={3} />
          <path className="illo-text" d={`M114 ${y + 2} H144`} />
        </g>
      ))}
    </Frame>
  );
}

export function EvidenceVerificationIllustration(p: IllustrationProps) {
  return (
    <Frame {...p} name="evidence">
      <Ground w={58} />
      <rect className="illo-surface illo-line" x={20} y={18} width={58} height={76} rx={4} />
      <path className="illo-text" d="M30 32 H66 M30 42 H58 M30 52 H64 M30 62 H54" />
      <rect className="illo-box illo-box-a" x={27} y={47} width={42} height={10} rx={2} />
      <path className="illo-line-thin illo-dash illo-flow" d="M70 52 C86 52 88 40 104 40" />
      <rect className="illo-wash illo-line" x={100} y={22} width={44} height={36} rx={5} />
      <path className="illo-text" d="M108 34 H136 M108 44 H128" />
      <g className="illo-float">
        <circle className="illo-seal" cx={118} cy={82} r={17} />
        <path className="illo-check-light" d="M110 82 L116 88 L127 76" />
      </g>
      <circle className="illo-line" cx={60} cy={92} r={11} fill="none" />
      <path className="illo-line" d="M68 100 L78 110" />
    </Frame>
  );
}

/** Every illustration by key, for galleries and data-driven pages. */
export const ILLUSTRATIONS = {
  anatomy: AnatomyIllustration,
  dna: DnaIllustration,
  heartbeat: HeartbeatIllustration,
  cell: CellIllustration,
  molecule: MoleculeIllustration,
  capsule: CapsuleIllustration,
  tablets: TabletsIllustration,
  prescription: PrescriptionIllustration,
  hospital: HospitalIllustration,
  patient: PatientIllustration,
  record: MedicalRecordIllustration,
  insurance: InsuranceShieldIllustration,
  scan: DocumentScanIllustration,
  ocr: OcrIllustration,
  evidence: EvidenceVerificationIllustration,
} as const;

export type IllustrationName = keyof typeof ILLUSTRATIONS;
