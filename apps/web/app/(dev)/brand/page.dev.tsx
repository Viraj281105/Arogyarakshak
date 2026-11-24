import { notFound } from "next/navigation";
import type { CSSProperties } from "react";
import { ArogyaEmblem, ArogyaLoader, ArogyaLogoAnimated, ArogyaWordmark } from "../../components/brand/Brand";
import { BACKGROUNDS } from "../../components/illustrations/Backgrounds";
import { ILLUSTRATIONS } from "../../components/illustrations/Illustrations";
import { PageHeader } from "../../components/ui/PageHeader";

// Dev-only gallery of the brand set, illustrations and ambient backgrounds (page.dev.tsx: not part of
// production builds, see next.config.ts). Reference for anyone building pages: import from
// components/brand/Brand and components/illustrations/*. Nothing here is data.
const swatch: CSSProperties = { display: "grid", gap: 8, justifyItems: "center", padding: 16, borderRadius: 16, border: "1px solid var(--border-subtle)", background: "var(--bg-surface)" };
const grid: CSSProperties = { display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", margin: "16px 0 40px" };
const forest: CSSProperties = { ...swatch, background: "var(--palette-deep-forest)", color: "var(--palette-warm-ivory)" };

export default function BrandGalleryPage() {
  if (process.env.NODE_ENV === "production") notFound();
  return (
    <div className="container" style={{ paddingBlock: 32 }}>
      <PageHeader
        kicker="Dev gallery"
        title="Brand, illustrations and backgrounds"
        lede="Deep Forest / Warm Ivory identity. Emblem, wordmark, animated logo and loader; 15 illustrations; 5 ambient backgrounds. All plain SVG and CSS, no JavaScript."
        breadcrumbs={[{ label: "Home", href: "/" }, { label: "Dev" }, { label: "Brand" }]}
      />

      <h2>Emblem and wordmark</h2>
      <div style={grid}>
        <div style={swatch}><ArogyaEmblem size={128} /><code>primary · light</code></div>
        <div style={forest}><ArogyaEmblem size={128} tone="dark" /><code>primary · dark</code></div>
        <div style={swatch}><ArogyaEmblem size={96} tone="mono-dark" /><code>mono-dark (print)</code></div>
        <div style={forest}><ArogyaEmblem size={96} tone="mono-light" /><code>mono-light</code></div>
        <div style={swatch}>
          <div style={{ display: "flex", gap: 12, alignItems: "end" }}>
            <ArogyaEmblem size={48} /><ArogyaEmblem size={32} /><ArogyaEmblem size={24} /><ArogyaEmblem size={16} />
          </div>
          <code>48 · 32 · 24 · 16 px (compact below 40)</code>
        </div>
        <div style={swatch}><ArogyaLogoAnimated size={112} /><code>ArogyaLogoAnimated (reload to replay)</code></div>
        <div style={swatch}><ArogyaLoader label="Reading your document…" /><code>ArogyaLoader</code></div>
      </div>
      <div style={{ display: "grid", gap: 16, margin: "0 0 40px" }}>
        <div style={{ ...swatch, justifyItems: "start" }}><ArogyaWordmark size={48} /></div>
        <div style={{ ...forest, justifyItems: "start" }}><ArogyaWordmark size={48} tone="dark" subline="Healthcare deserves transparency" /></div>
      </div>

      <h2>Illustrations (animated)</h2>
      <div style={grid}>
        {Object.entries(ILLUSTRATIONS).map(([name, Illo]) => (
          <figure key={name} style={swatch}>
            <Illo animate />
            <figcaption><code>{name}</code></figcaption>
          </figure>
        ))}
      </div>

      <h2>Ambient backgrounds</h2>
      <div style={{ display: "grid", gap: 16, margin: "16px 0 40px" }}>
        {Object.entries(BACKGROUNDS).map(([name, Bg]) => (
          <div key={name} style={{ position: "relative", height: 420, borderRadius: 16, border: "1px solid var(--border-subtle)", background: "var(--bg-base)", overflow: "hidden" }}>
            <Bg intensity={0.9} />
            <code style={{ position: "relative", zIndex: 1, display: "inline-block", margin: 16, padding: "4px 8px", background: "var(--bg-surface)", borderRadius: 6 }}>{name}</code>
          </div>
        ))}
      </div>
    </div>
  );
}
