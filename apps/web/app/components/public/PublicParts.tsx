import React from "react";
import "./public.css";
import { Breadcrumbs, type Crumb } from "../ui/PageHeader";
import { EVIDENCE_COPY, EVIDENCE_STATES, type EvidenceState } from "../ui/evidence";
import { PublicLanguageNotice } from "./PublicLanguageNotice";
import { PUBLIC_ICON_NODES, type PublicIconName } from "./publicIcons";
import { platformModuleHref, type PublicModuleId } from "./publicNav";
import type { FaqItem, Link, ModuleCopy } from "./copy/types";

// Server Components shared by the public pages (Wave 3 M3). No hooks; the only client code they
// render is PublicLanguageNotice. Icons are drawn from static SVG data (publicIcons.ts), not
// lucide-react components, which are client components (see that file for why it matters).

/** A lucide-geometry icon as plain server-rendered SVG, decorative. */
export function StaticIcon({ name, size = 20 }: { name: PublicIconName; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {PUBLIC_ICON_NODES[name].map(([tag, attrs], i) => React.createElement(tag, { key: i, ...attrs }))}
    </svg>
  );
}

/**
 * The evidence badge for server-rendered public pages: the same markup, classes, label, meaning and
 * icon geometry as components/ui/Badges.tsx EvidenceBadge, without the client icon component.
 */
export function EvidenceBadge({ state, size = "md" }: { state: EvidenceState; size?: "sm" | "md" }) {
  const copy = EVIDENCE_COPY[state];
  return (
    <span className="ui-evidence-wrap">
      <span className={`ui-badge ui-evidence ui-evidence-${state} ui-badge-${size}`} title={copy.meaning} data-evidence={state}>
        <StaticIcon name={state} size={size === "sm" ? 12 : 14} />
        <span>{copy.label}</span>
      </span>
    </span>
  );
}

export function ArrowIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

/** Page frame: accent backdrop, the language notice and the shell container. */
export function PublicPage({ module, children }: { module?: PublicModuleId; children: React.ReactNode }) {
  return (
    <div className="pub" data-module={module}>
      <div className="pub-backdrop" aria-hidden="true" />
      <div className="shell-container">
        <PublicLanguageNotice />
        {children}
      </div>
    </div>
  );
}

export function PublicHero({
  kicker,
  title,
  lede,
  breadcrumbs,
  actions,
  aside,
}: {
  kicker: string;
  title: React.ReactNode;
  lede: React.ReactNode;
  breadcrumbs?: readonly Crumb[];
  actions?: React.ReactNode;
  aside?: React.ReactNode;
}) {
  return (
    <header className="pub-hero">
      <div className="pub-hero-text">
        {breadcrumbs && <Breadcrumbs items={breadcrumbs} />}
        <p className="pub-kicker">{kicker}</p>
        <h1 className="pub-title">{title}</h1>
        <p className="pub-lede">{lede}</p>
        {actions && <div className="pub-actions">{actions}</div>}
      </div>
      {aside && <div className="pub-hero-aside">{aside}</div>}
    </header>
  );
}

/** A titled section; `id` names its heading for aria-labelledby. */
export function Section({
  id,
  kicker,
  heading,
  lede,
  children,
  className = "",
}: {
  id: string;
  kicker?: string;
  heading: string;
  lede?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`pub-section ${className}`.trim()} aria-labelledby={`${id}-title`}>
      <div className="pub-section-head pub-reveal">
        {kicker && <p className="pub-kicker">{kicker}</p>}
        <h2 id={`${id}-title`} className="pub-h2">
          {heading}
        </h2>
        {lede && <p className="pub-section-lede">{lede}</p>}
      </div>
      {children}
    </section>
  );
}

export function ModuleMark({ id, size = "md" }: { id: PublicModuleId; size?: "md" | "lg" }) {
  return (
    <span className={`pub-mark${size === "lg" ? " pub-mark-lg" : ""}`} data-module={id} aria-hidden="true">
      <StaticIcon name={id} size={size === "lg" ? 28 : 20} />
    </span>
  );
}

/** Card for one capability: the whole card is one link (no nested interactive content). */
export function ModuleCard({ module, linkLabel, headingLevel = 3 }: { module: ModuleCopy; linkLabel: string; headingLevel?: 2 | 3 }) {
  const H = headingLevel === 2 ? "h2" : "h3";
  return (
    <article className="pub-card pub-module-card pub-card-accent" data-module={module.id}>
      <div className="pub-module-card-head">
        <ModuleMark id={module.id} />
        <div>
          <H className="pub-module-name">{module.name}</H>
          <span className="pub-module-native">
            <span lang="hi">{module.native}</span> · {module.meaning}
          </span>
        </div>
      </div>
      <p className="pub-module-role">{module.role}</p>
      <p>{module.lede}</p>
      <a className="pub-link pub-stretch" href={platformModuleHref(module.id)}>
        {linkLabel}
        <span className="sr-only">: {module.name}</span>
        <ArrowIcon />
      </a>
    </article>
  );
}

/** The eight evidence states with their meaning (the single vocabulary, components/ui/evidence.ts). */
export function EvidenceLegend({ states = EVIDENCE_STATES }: { states?: readonly EvidenceState[] }) {
  return (
    <ul className="pub-evidence">
      {states.map((s) => (
        <li key={s} className="pub-reveal">
          <EvidenceBadge state={s} />
          <p>{EVIDENCE_COPY[s].meaning}</p>
        </li>
      ))}
    </ul>
  );
}

export function EvidenceBadges({ states }: { states: readonly EvidenceState[] }) {
  return (
    <span className="pub-badges">
      {states.map((s) => (
        <EvidenceBadge key={s} state={s} size="sm" />
      ))}
    </span>
  );
}

export function CtaBand({ id, heading, body, primary, secondary }: { id: string; heading: string; body: string; primary: Link; secondary?: Link }) {
  return (
    <section className="pub-cta pub-reveal" aria-labelledby={`${id}-title`}>
      <h2 id={`${id}-title`} className="pub-h2">
        {heading}
      </h2>
      <p>{body}</p>
      <div className="pub-actions">
        <a className="btn btn-primary btn-lg" href={primary.href}>
          {primary.label}
          <ArrowIcon size={18} />
        </a>
        {secondary && (
          <a className="btn btn-ghost btn-lg" href={secondary.href}>
            {secondary.label}
          </a>
        )}
      </div>
    </section>
  );
}

/** Static FAQ as native disclosures (no JS). */
export function FaqList({ items }: { items: readonly FaqItem[] }) {
  return (
    <ul className="pub-faq">
      {items.map((f) => (
        <li key={f.id} id={`faq-${f.id}`}>
          <details>
            <summary>{f.question}</summary>
            <div className="pub-faq-answer">
              {f.answer.map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
          </details>
        </li>
      ))}
    </ul>
  );
}
