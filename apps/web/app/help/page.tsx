import type { Metadata } from "next";
import { HelpSearch } from "../components/public/HelpSearch";
import { ArrowIcon, CtaBand, ModuleMark, PublicHero, PublicPage, Section } from "../components/public/PublicParts";
import { localisedPublicCopy, pageTitle } from "../components/public/publicCopy";
import { PUBLIC_ROUTES, platformModuleHref } from "../components/public/publicNav";
import { requestLanguage } from "../i18n/server";


export async function generateMetadata(): Promise<Metadata> {
  const { meta } = (await localisedPublicCopy(await requestLanguage())).help;
  return { title: pageTitle(meta.title), description: meta.description };
}

/** /help (Server Component): searchable FAQ (client filter over static props), module guides, deletion. */
export default async function HelpPage() {
  const c = await localisedPublicCopy(await requestLanguage());
  const h = c.help;
  return (
    <PublicPage module="dawacheck">
      <PublicHero
        kicker={h.kicker}
        title={h.headline}
        lede={h.lede}
        breadcrumbs={[{ label: c.common.breadcrumbHome, href: "/" }, { label: h.kicker }]}
        actions={
          <>
            <a className="btn btn-ghost btn-lg" href="#help-guides-title">
              {h.guidesHeading}
            </a>
            <a className="btn btn-ghost btn-lg" href="#help-delete-title">
              {h.deletion.heading}
            </a>
          </>
        }
      />

      <Section id="help-faq" heading={h.faqHeading}>
        <HelpSearch items={c.faq} labels={h.search} />
      </Section>

      <Section id="help-guides" heading={h.guidesHeading} lede={h.guidesLede}>
        <ul className="pub-grid pub-grid-2">
          {h.guides.map((g) => {
            const m = c.modules[g.id];
            return (
              <li key={g.id} className="pub-card pub-card-accent pub-reveal" data-module={g.id}>
                <div className="pub-module-card-head">
                  <ModuleMark id={g.id} />
                  <h3 className="pub-module-name">{m.name}</h3>
                </div>
                <dl className="pub-facts">
                  <div>
                    <dt>{h.guideReady}</dt>
                    <dd>
                      <ul className="pub-list">
                        {g.ready.map((r) => (
                          <li key={r}>{r}</li>
                        ))}
                      </ul>
                    </dd>
                  </div>
                  <div>
                    <dt>{h.guideWhere}</dt>
                    <dd>
                      <a className="pub-link" href={m.cta.href}>
                        {g.where}
                        <ArrowIcon />
                      </a>
                    </dd>
                  </div>
                </dl>
                <p className="pub-card-body">
                  <a className="pub-link" href={platformModuleHref(g.id)}>
                    {c.common.learnMore}
                    <span className="sr-only">: {m.name}</span>
                    <ArrowIcon />
                  </a>
                </p>
              </li>
            );
          })}
        </ul>
      </Section>

      <Section id="help-delete" heading={h.deletion.heading}>
        <ul className="pub-grid">
          {h.deletion.items.map((d) => (
            <li key={d.title} className="pub-card pub-reveal">
              <h3 className="pub-h3">{d.title}</h3>
              <p>{d.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <CtaBand id="help-cta" heading={c.landing.finalCta.heading} body={c.landing.finalCta.body} primary={c.landing.primaryCta} secondary={{ label: c.security.kicker, href: PUBLIC_ROUTES.security }} />
    </PublicPage>
  );
}
