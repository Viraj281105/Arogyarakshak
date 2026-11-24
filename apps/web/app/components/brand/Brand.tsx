// ArogyaRakshak brand components. No hooks and no client directive: they render as plain SVG from Server
// Components and are cheap to import from Client Components too. All animation is CSS (brand.css),
// stopped by prefers-reduced-motion and by the in-app setting (data-motion="reduce").
import type { CSSProperties } from "react";
import {
  COMPACT,
  CROSS_H,
  CROSS_V,
  HEAD,
  LEAF_LEFT,
  LEAF_RIGHT,
  SHIELD,
  SHIELD_INNER,
  TORSO,
  VEIN_LEFT,
  VEIN_RIGHT,
  emblemPaint,
  type EmblemTone,
} from "./geometry";

type A11y = { title?: string; decorative?: boolean };

function a11yProps({ title = "ArogyaRakshak", decorative = false }: A11y) {
  return decorative ? { "aria-hidden": true as const, focusable: "false" as const } : { role: "img", "aria-label": title };
}

export type EmblemProps = A11y & {
  /** Rendered size in px (square). Below 40 px the compact symbol is used automatically. */
  size?: number;
  tone?: EmblemTone;
  /** Force a variant; "auto" picks compact below 40 px. */
  variant?: "auto" | "primary" | "compact";
  className?: string;
  /** Adds the path-drawing reveal (ArogyaLogoAnimated) or the loading pulse (ArogyaLoader). */
  motion?: "none" | "reveal" | "loading";
  style?: CSSProperties;
};

/** The emblem: shield, leaves cradling a human figure, medical cross. */
export function ArogyaEmblem({
  size = 48,
  tone = "light",
  variant = "auto",
  className,
  motion = "none",
  style,
  ...a11y
}: EmblemProps) {
  const p = emblemPaint(tone);
  const compact = variant === "compact" || (variant === "auto" && size < 40);
  const mono = tone === "mono-light";
  const cls = ["ar-emblem", motion !== "none" ? `ar-emblem--${motion}` : "", className].filter(Boolean).join(" ");

  if (compact) {
    return (
      <svg viewBox="0 0 32 32" width={size} height={size} className={cls} style={style} {...a11yProps(a11y)}>
        <path className="ar-e-shield" pathLength={100} d={COMPACT.shield} fill={p.shield} stroke={p.shieldStroke} strokeWidth={mono ? 2 : 1} strokeLinejoin="round" />
        <path className="ar-e-leaf ar-e-leaf-l" d={COMPACT.leafLeft} fill={p.leaf} />
        <path className="ar-e-leaf ar-e-leaf-r" d={COMPACT.leafRight} fill={p.leaf} />
        <path className="ar-e-cross" pathLength={100} d={`${COMPACT.crossV} ${COMPACT.crossH}`} fill="none" stroke={p.figure} strokeWidth={3} strokeLinecap="round" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 64 64" width={size} height={size} className={cls} style={style} {...a11yProps(a11y)}>
      <path className="ar-e-shield" pathLength={100} d={SHIELD} fill={p.shield} stroke={p.shieldStroke} strokeWidth={mono ? 2.5 : 1.5} strokeLinejoin="round" />
      {!mono && size >= 48 && <path className="ar-e-inner" pathLength={100} d={SHIELD_INNER} fill="none" stroke={p.inner} strokeWidth={0.8} strokeOpacity={0.35} />}
      <path className="ar-e-leaf ar-e-leaf-l" d={LEAF_LEFT} fill={p.leaf} />
      <path className="ar-e-leaf ar-e-leaf-r" d={LEAF_RIGHT} fill={p.leaf} />
      {p.vein !== "none" && (
        <path className="ar-e-vein" pathLength={100} d={`${VEIN_LEFT} ${VEIN_RIGHT}`} fill="none" stroke={p.vein} strokeWidth={0.9} strokeLinecap="round" strokeOpacity={0.55} />
      )}
      <g className="ar-e-figure">
        <circle cx={HEAD.cx} cy={HEAD.cy} r={HEAD.r} fill={p.figure} />
        <path d={TORSO} fill={p.figure} stroke={mono ? "none" : p.shield} strokeWidth={1.4} paintOrder="stroke" />
      </g>
      <path className="ar-e-cross" pathLength={100} d={`${CROSS_V} ${CROSS_H}`} fill="none" stroke={p.cross} strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}

export type WordmarkProps = {
  /** Emblem size in px; the type scales with it. */
  size?: number;
  tone?: "light" | "dark";
  /** Show आरोग्यरक्षक under the name. */
  devanagari?: boolean;
  /** Optional line under the name (for example the tagline); replaces the Devanagari line. */
  subline?: string;
  className?: string;
  /** The wordmark is usually inside a link that has its own label. */
  decorative?: boolean;
};

/** Horizontal lockup: emblem + "ArogyaRakshak" in Manrope (real text, so it is crisp and translatable). */
export function ArogyaWordmark({ size = 36, tone = "light", devanagari = true, subline, className, decorative = false }: WordmarkProps) {
  return (
    <span
      className={["ar-wordmark", `ar-wordmark--${tone}`, className].filter(Boolean).join(" ")}
      style={{ "--ar-wordmark-size": `${size}px` } as CSSProperties}
      {...(decorative ? { "aria-hidden": true } : {})}
    >
      <ArogyaEmblem size={size} tone={tone === "dark" ? "dark" : "light"} decorative />
      <span className="ar-wordmark-text">
        <span className="ar-wordmark-name">
          Arogya<span className="ar-wordmark-name-b">Rakshak</span>
        </span>
        {subline ? (
          <span className="ar-wordmark-sub">{subline}</span>
        ) : devanagari ? (
          <span className="ar-wordmark-sub" lang="hi">
            आरोग्यरक्षक
          </span>
        ) : null}
      </span>
    </span>
  );
}

/** The emblem drawing itself in (shield contour, leaves grow, figure rises, cross draws). Plays once. */
export function ArogyaLogoAnimated({ size = 96, tone = "light", ...a11y }: Omit<EmblemProps, "motion" | "variant">) {
  return <ArogyaEmblem size={size} tone={tone} variant="primary" motion="reveal" {...a11y} />;
}

/**
 * Branded loading indicator. role="status" with a visible label, so it is announced; under reduced
 * motion it is the still emblem plus the label.
 */
export function ArogyaLoader({ label = "Loading…", size = 56, tone = "light", inline = false }: { label?: string; size?: number; tone?: EmblemTone; inline?: boolean }) {
  return (
    <div className={inline ? "ar-loader ar-loader--inline" : "ar-loader"} role="status" aria-live="polite">
      <ArogyaEmblem size={size} tone={tone} variant="primary" motion="loading" decorative />
      <span className="ar-loader-label">{label}</span>
    </div>
  );
}
