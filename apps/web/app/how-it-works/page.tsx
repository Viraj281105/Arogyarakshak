import type { Metadata } from "next";
import { ArrowIcon, CtaBand, EvidenceBadges, PublicHero, PublicPage, Section } from "../components/public/PublicParts";
import { localisedPublicCopy, pageTitle } from "../components/public/publicCopy";
import { PUBLIC_ROUTES } from "../components/public/publicNav";
import { requestLanguage } from "../i18n/server";


export async function generateMetadata(): Promise<Metadata> {
  const { meta } = (await localisedPublicCopy(await requestLanguage())).howItWorks;
  return { title: pageTitle(meta.title), description: meta.description };
}

/** /how-it-works (Server Component): upload → extract → analyse → verify → understand → act. */
export default async function HowItWorksPage() {
  const c = await localisedPublicCopy(await requestLanguage());
  const h = c.howItWorks;
  return (
    <PublicPage module="billnyay">
      <PublicHero
        kicker={h.kicker}
        title={h.headline}
        lede={h.lede}
        breadcrumbs={[{ label: c.common.breadcrumbHome, href: "/" }, { label: h.kicker }]}
        actions={
          <a className="btn btn-primary btn-lg" href={c.landing.primaryCta.href}>
            {c.common.checkDocument}
            <ArrowIcon size={18} />
          </a>
        }
      />

      <section className="pub-section" aria-labelledby="hw-stages-title">
        <h2 id="hw-stages-title" className="sr-only">
          {h.kicker}
        </h2>
        <ol className="pub-stages">
          {h.stages.map((s, i) => (
            <li key={s.verb} className="pub-stage pub-reveal">
              <p className="pub-stage-verb" aria-hidden="true">
                <small>0{i + 1}</small>
                {s.verb}
              </p>
              <div className="pub-stage-body">
                <h3 className="pub-h3">
                  <span className="sr-only">
                    {i + 1}. {s.verb}:{" "}
                  </span>
                  {s.title}
                </h3>
                <p>{s.body}</p>
                <dl className="pub-facts">
                  <div>
                    <dt>{h.keptLabel}</dt>
                    <dd>{s.kept}</dd>
                  </div>
                  <div>
                    <dt>{h.evidenceLabel}</dt>
                    <dd>
                      <EvidenceBadges states={s.evidence} />
                    </dd>
                  </div>
                </dl>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <Section id="hw-sharing" kicker={h.sharing.kicker} heading={h.sharing.heading} lede={h.sharing.lede}>
        <ul className="pub-grid">
          {h.sharing.steps.map((s, i) => (
            <li key={s.title} className="pub-card pub-reveal" data-module="kadi">
              <span className="pub-num" aria-hidden="true">
                0{i + 1}
              </span>
              <h3 className="pub-h3">{s.title}</h3>
              <p>{s.body}</p>
            </li>
          ))}
        </ul>
        <p className="pub-note">
          <a className="pub-link" href={PUBLIC_ROUTES.platform}>
            {c.common.explorePlatform}
            <ArrowIcon />
          </a>
        </p>
      </Section>

      <Section id="hw-control" kicker={h.control.kicker} heading={h.control.heading}>
        <ul className="pub-grid">
          {h.control.items.map((s) => (
            <li key={s.title} className="pub-card pub-reveal">
              <h3 className="pub-h3">{s.title}</h3>
              <p>{s.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <CtaBand id="hw-cta" heading={c.landing.finalCta.heading} body={c.landing.finalCta.body} primary={c.landing.primaryCta} secondary={{ label: c.security.kicker, href: PUBLIC_ROUTES.security }} />
    </PublicPage>
  );
}
