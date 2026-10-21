import React from "react";
import { ILLUSTRATIVE_LINES, LineStatus, formatINR } from "../../lib/illustrativeBill";

const ROW_Y0 = 132;
const ROW_GAP = 56;

const Mark: React.FC<{ status: LineStatus; cx: number; cy: number }> = ({ status, cx, cy }) => {
  switch (status) {
    case "within_benchmark":
      return (
        <g className="ill-mark ill-mark-within">
          <circle cx={cx} cy={cy} r={11} />
          <path d={`M${cx - 5} ${cy} l3.5 3.5 l6.5 -7`} />
        </g>
      );
    case "overcharged":
      return (
        <g className="ill-mark ill-mark-over">
          <circle cx={cx} cy={cy} r={11} />
          <path d={`M${cx} ${cy + 5} V${cy - 5} M${cx - 4} ${cy - 1} l4 -4 l4 4`} />
        </g>
      );
    case "bundled":
      return (
        <g className="ill-mark ill-mark-bundled">
          <circle cx={cx} cy={cy} r={11} />
          <circle cx={cx} cy={cy} r={4} />
        </g>
      );
    default:
      return (
        <g className="ill-mark ill-mark-unmatched">
          <circle cx={cx} cy={cy} r={11} />
          <path d={`M${cx - 5} ${cy} H${cx + 5}`} />
        </g>
      );
  }
};

/**
 * The landing hero's drawing: the illustrative bill being read line by line. Purely
 * decorative (the same lines are explained in text further down the page), so it is hidden
 * from assistive technology.
 */
export const HeroIllustration: React.FC = () => {
  const ward = ILLUSTRATIVE_LINES.find((l) => l.id === "ward");
  const total = ILLUSTRATIVE_LINES.reduce((s, l) => s + l.billed, 0);
  return (
    <svg className="hero-ill" viewBox="0 0 420 560" role="presentation" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id="ill-scan" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" className="ill-scan-stop-edge" />
          <stop offset="0.55" className="ill-scan-stop-core" />
          <stop offset="1" className="ill-scan-stop-edge" />
        </linearGradient>
        <clipPath id="ill-sheet-clip">
          <rect x="34" y="28" width="336" height="452" rx="18" />
        </clipPath>
      </defs>

      <g className="ill-layer-back">
        <rect className="ill-sheet-back" x="58" y="44" width="330" height="444" rx="18" transform="rotate(4 223 266)" />
      </g>

      <g className="ill-layer-front">
        <rect className="ill-sheet" x="34" y="28" width="336" height="452" rx="18" />
        <rect className="ill-sheet-margin" x="34" y="28" width="6" height="452" rx="3" />

        <text className="ill-kicker" x="62" y="66">INPATIENT BILL</text>
        <text className="ill-kicker ill-kicker-soft" x="342" y="66" textAnchor="end">ILLUSTRATIVE</text>
        <line className="ill-rule" x1="62" x2="342" y1="84" y2="84" />
        <text className="ill-col" x="62" y="106">Item</text>
        <text className="ill-col" x="300" y="106" textAnchor="end">Billed</text>

        {ILLUSTRATIVE_LINES.map((line, i) => {
          const y = ROW_Y0 + i * ROW_GAP;
          return (
            <g key={line.id} className="ill-row" style={{ "--row": i } as React.CSSProperties}>
              <text className="ill-label" x="62" y={y}>{line.label}</text>
              <text className="ill-sub" x="62" y={y + 18}>{line.quantity}</text>
              <text className="ill-amount" x="300" y={y} textAnchor="end">{formatINR(line.billed)}</text>
              <line className="ill-row-rule" x1="62" x2="342" y1={y + 32} y2={y + 32} />
              <Mark status={line.status} cx={330} cy={y - 5} />
            </g>
          );
        })}

        <text className="ill-total-label" x="62" y="430">Total billed</text>
        <text className="ill-total" x="300" y="430" textAnchor="end">{formatINR(total)}</text>

        <g clipPath="url(#ill-sheet-clip)">
          <rect className="ill-scan" x="34" y="92" width="336" height="44" fill="url(#ill-scan)" />
        </g>
      </g>

      {ward && ward.reference !== null && ward.rate && (
        <g className="ill-note">
          <path className="ill-note-leader" d="M346 127 C 392 132, 396 300, 392 494" />
          <rect className="ill-note-box" x="196" y="494" width="220" height="58" rx="10" />
          <text className="ill-note-title" x="212" y="516">Ward · CGHS reference</text>
          <text className="ill-note-body" x="212" y="538">
            {formatINR(ward.rate.rate)}/day · billed {formatINR(ward.billed / (ward.reference / ward.rate.rate))}
          </text>
        </g>
      )}
    </svg>
  );
};
