import type { Metadata } from "next";
import { ArrowIcon, CtaBand, EvidenceLegend, ModuleCard, ModuleMark, PublicHero, PublicPage, Section } from "../components/public/PublicParts";
import { localisedPublicCopy, pageTitle } from "../components/public/publicCopy";
import { PUBLIC_MODULE_IDS, platformModuleHref } from "../components/public/publicNav";
import { requestLanguage } from "../i18n/server";


export async function generateMetadata(): Promise<Metadata> {
  const { meta } = (await localisedPublicCopy(await requestLanguage())).platform;
  return { title: pageTitle(meta.title), description: meta.description };
}

const CHECKS = PUBLIC_MODULE_IDS.filter((id) => id !== "kadi");
const SLOTS = ["a", "b", "c", "d", "e"] as const;

/** /platform (Server Component): how the parts fit together. */
export default async function PlatformPage() {
  const c = await localisedPublicCopy(await requestLanguage());
  const p = c.platform;
  return (
    <PublicPage module="kadi">
      <PublicHero
        kicker={p.kicker}
        title={p.headline}
        lede={p.lede}
        breadcrumbs={[{ label: c.common.breadcrumbHome, href: "/" }, { label: p.kicker }]}
        actions={
          <>
            <a className="btn btn-primary btn-lg" href={c.landing.primaryCta.href}>
              {c.common.checkDocument}
              <ArrowIcon size={18} />
            </a>
            <a className="btn btn-ghost btn-lg" href="/how-it-works">
              {c.howItWorks.kicker}
            </a>
          </>
        }
      />

      <Section id="pf-eco" kicker={p.ecosystem.kicker} heading={p.ecosystem.heading} lede={p.ecosystem.lede}>
        <ul className="pub-eco pub-reveal">
          <li className="pub-eco-hub" data-module="kadi">
            <ModuleMark id="kadi" size="lg" />
            <h3 className="pub-module-name">
              <a className="pub-link" href={platformModuleHref("kadi")}>
                {p.ecosystem.hubLabel}
                <ArrowIcon />
              </a>
            </h3>
            <p>{p.ecosystem.hubBody}</p>
          </li>
          {CHECKS.map((id, i) => {
            const m = c.modules[id];
            return (
              <li key={id} className="pub-eco-item" data-slot={SLOTS[i]}>
                <article className="pub-card pub-module-card pub-card-accent" data-module={id}>
                  <div className="pub-module-card-head">
                    <ModuleMark id={id} />
                    <div>
                      <h3 className="pub-module-name">{m.name}</h3>
                      <span className="pub-module-native">{m.role}</span>
                    </div>
                  </div>
                  <p>
                    {c.landing.capabilities.checksAgainst}: {m.against}
                  </p>
                  <a className="pub-link pub-stretch" href={platformModuleHref(id)}>
                    {c.common.learnMore}
                    <span className="sr-only">: {m.name}</span>
                    <ArrowIcon />
                  </a>
                </article>
              </li>
            );
          })}
        </ul>
      </Section>

      <Section id="pf-kadi" kicker={p.kadi.kicker} heading={p.kadi.heading} lede={p.kadi.lede}>
        <ul className="pub-grid">
          {p.kadi.items.map((item) => (
            <li key={item.title} className="pub-card pub-reveal" data-module="kadi">
              <h3 className="pub-h3">{item.title}</h3>
              <p>{item.body}</p>
            </li>
          ))}
        </ul>
        <p className="pub-note">
          <a className="pub-link" href={p.kadi.link.href}>
            {p.kadi.link.label}
            <ArrowIcon />
          </a>
        </p>
      </Section>

      <Section id="pf-context" kicker={p.context.kicker} heading={p.context.heading}>
        <div className="pub-split">
          <div className="pub-prose pub-reveal">
            {p.context.lede.map((t) => (
              <p key={t}>{t}</p>
            ))}
            <ul className="pub-list">
              {p.context.notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          </div>
          <div className="pub-table-wrap pub-reveal" tabIndex={0} role="region" aria-labelledby="pf-context-caption">
            <table className="pub-table">
              <caption id="pf-context-caption">{p.context.statesCaption}</caption>
              <tbody>
                {p.context.states.map((s) => (
                  <tr key={s.state}>
                    <th scope="row">
                      <span className="pub-code">{s.state}</span>
                    </th>
                    <td>{s.meaning}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      <Section id="pf-evidence" kicker={p.evidence.kicker} heading={p.evidence.heading} lede={p.evidence.lede}>
        <EvidenceLegend />
        <h3 className="pub-h3 pub-subhead">
          {p.evidence.provenanceHeading}
        </h3>
        <ul className="pub-grid">
          {p.evidence.provenance.map((item) => (
            <li key={item.title} className="pub-card pub-reveal">
              <h4 className="pub-h3">{item.title}</h4>
              <p>{item.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section id="pf-access" kicker={p.access.kicker} heading={p.access.heading} lede={p.access.lede}>
        <div className="pub-table-wrap pub-reveal" tabIndex={0} role="region" aria-labelledby="pf-access-caption">
          <table className="pub-table">
            <caption id="pf-access-caption">{p.access.caption}</caption>
            <thead>
              <tr>
                <td />
                <th scope="col">{p.access.columns[1]}</th>
              </tr>
            </thead>
            <tbody>
              {p.access.rows.map((r) => (
                <tr key={r.aspect}>
                  <th scope="row">{r.aspect}</th>
                  <td>{r.account}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="pub-note">{p.access.note}</p>
      </Section>

      <Section id="pf-review" heading={p.review.heading} lede={p.review.body}>
        <p className="pub-note">
          <a className="pub-link" href={p.review.link.href}>
            {p.review.link.label}
            <ArrowIcon />
          </a>
        </p>
      </Section>

      <Section id="pf-modules" heading={p.modulesHeading}>
        <ul className="pub-grid">
          {PUBLIC_MODULE_IDS.map((id) => (
            <li key={id} className="pub-reveal">
              <ModuleCard module={c.modules[id]} linkLabel={c.common.learnMore} />
            </li>
          ))}
        </ul>
      </Section>

      <CtaBand id="pf-cta" heading={c.landing.finalCta.heading} body={c.landing.finalCta.body} primary={c.landing.primaryCta} secondary={{ label: c.help.kicker, href: "/help" }} />
    </PublicPage>
  );
}
