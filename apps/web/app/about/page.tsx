import type { Metadata } from "next";
import { CtaBand, ModuleCard, PublicHero, PublicPage, Section } from "../components/public/PublicParts";
import { pageTitle, publicCopy } from "../components/public/publicCopy";
import { PUBLIC_MODULE_IDS, PUBLIC_ROUTES } from "../components/public/publicNav";

const c = publicCopy();
const a = c.about;

export const metadata: Metadata = { title: pageTitle(a.meta.title), description: a.meta.description };

/** /about (Server Component): mission, principles, names, what it is not, how it is built. */
export default function AboutPage() {
  return (
    <PublicPage module="schemesetu">
      <PublicHero
        kicker={a.kicker}
        title={a.headline}
        lede={a.lede}
        breadcrumbs={[{ label: c.common.breadcrumbHome, href: "/" }, { label: a.kicker }]}
      />

      <Section id="ab-mission" heading={a.mission.heading}>
        <div className="pub-prose pub-reveal">
          {a.mission.body.map((t) => (
            <p key={t}>{t}</p>
          ))}
        </div>
      </Section>

      <Section id="ab-principles" heading={a.principlesHeading}>
        <ol className="pub-grid">
          {a.principles.map((p, i) => (
            <li key={p.title} className="pub-card pub-reveal">
              <span className="pub-num" aria-hidden="true">
                0{i + 1}
              </span>
              <h3 className="pub-h3">{p.title}</h3>
              <p>{p.body}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section id="ab-names" heading={a.names.heading} lede={a.names.lede}>
        <ul className="pub-grid">
          {PUBLIC_MODULE_IDS.map((id) => (
            <li key={id} className="pub-reveal">
              <ModuleCard module={c.modules[id]} linkLabel={c.common.learnMore} />
            </li>
          ))}
        </ul>
      </Section>

      <Section id="ab-not" heading={a.isNot.heading}>
        <ul className="pub-list pub-list-limits pub-reveal">
          {a.isNot.items.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      </Section>

      <Section id="ab-built" heading={a.built.heading}>
        <ul className="pub-grid">
          {a.built.items.map((b) => (
            <li key={b.title} className="pub-card pub-reveal">
              <h3 className="pub-h3">{b.title}</h3>
              <p>{b.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <CtaBand id="ab-cta" heading={c.landing.finalCta.heading} body={c.landing.finalCta.body} primary={c.landing.primaryCta} secondary={{ label: c.security.kicker, href: PUBLIC_ROUTES.security }} />
    </PublicPage>
  );
}
