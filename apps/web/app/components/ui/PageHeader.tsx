import React from "react";

export interface Crumb {
  label: string;
  /** Omit on the current page (the last crumb). */
  href?: string;
}

/** Breadcrumb trail: a labelled nav with an ordered list; the current page has aria-current. */
export function Breadcrumbs({ items, label = "Breadcrumb" }: { items: readonly Crumb[]; label?: string }) {
  if (items.length === 0) return null;
  return (
    <nav className="ui-breadcrumbs" aria-label={label}>
      <ol>
        {items.map((c, i) => {
          const last = i === items.length - 1;
          return (
            <li key={`${c.label}-${i}`}>
              {c.href && !last ? <a href={c.href}>{c.label}</a> : <span aria-current={last ? "page" : undefined}>{c.label}</span>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/** Page title block: optional breadcrumbs, kicker, the one <h1>, a lede and right-aligned actions. */
export function PageHeader({
  title,
  kicker,
  lede,
  breadcrumbs,
  actions,
}: {
  title: React.ReactNode;
  kicker?: string;
  lede?: React.ReactNode;
  breadcrumbs?: readonly Crumb[];
  actions?: React.ReactNode;
}) {
  return (
    <header className="ui-page-header">
      {breadcrumbs && <Breadcrumbs items={breadcrumbs} />}
      <div className="ui-page-header-row">
        <div className="ui-page-header-text">
          {kicker && <p className="ui-kicker">{kicker}</p>}
          <h1 className="ui-page-title">{title}</h1>
          {lede && <p className="ui-page-lede">{lede}</p>}
        </div>
        {actions && <div className="ui-page-actions">{actions}</div>}
      </div>
    </header>
  );
}
