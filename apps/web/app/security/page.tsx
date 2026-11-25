import type { Metadata } from "next";
import { ArrowIcon, CtaBand, PublicHero, PublicPage, Section } from "../components/public/PublicParts";
import { localisedPublicCopy, pageTitle } from "../components/public/publicCopy";
import { PUBLIC_ROUTES } from "../components/public/publicNav";
import { requestLanguage } from "../i18n/server";


export async function generateMetadata(): Promise<Metadata> {
  const { meta } = (await localisedPublicCopy(await requestLanguage())).security;
  return { title: pageTitle(meta.title), description: meta.description };
}

/** /security (Server Component): implemented controls only, each with where to check it; then the limits. */
export default async function SecurityPage() {
  const c = await localisedPublicCopy(await requestLanguage());
  const s = c.security;
  return (
    <PublicPage module="bimanyay">
      <PublicHero
        kicker={s.kicker}
        title={s.headline}
        lede={s.lede}
        breadcrumbs={[{ label: c.common.breadcrumbHome, href: "/" }, { label: s.kicker }]}
        actions={
          <>
            <a className="btn btn-ghost btn-lg" href="#sec-limits-title">
              {s.limitsHeading}
            </a>
            <a className="btn btn-ghost btn-lg" href="#sec-flow-title">
              {s.flowHeading}
            </a>
          </>
        }
      />

      <Section id="sec-controls" heading={s.controlsHeading}>
        <ul className="pub-grid pub-grid-2">
          {s.controls.map((ctl) => (
            <li key={ctl.title} className="pub-card pub-reveal">
              <h3 className="pub-h3">{ctl.title}</h3>
              <p>{ctl.body}</p>
              <p className="pub-card-source">
                {c.common.sourcePrefix}: {ctl.source}
              </p>
            </li>
          ))}
        </ul>
      </Section>

      <Section id="sec-flow" heading={s.flowHeading} lede={s.flowLede}>
        <div className="pub-table-wrap pub-reveal" tabIndex={0} role="region" aria-labelledby="sec-flow-caption">
          <table className="pub-table">
            <caption id="sec-flow-caption">{s.flowLede}</caption>
            <thead>
              <tr>
                {s.flowColumns.map((col) => (
                  <th key={col} scope="col">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {s.flow.map((row) => (
                <tr key={row.what}>
                  <th scope="row">{row.what}</th>
                  <td>{row.where}</td>
                  <td>{row.when}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section id="sec-limits" heading={s.limitsHeading} lede={s.limitsLede}>
        <ul className="pub-grid pub-grid-2">
          {s.limits.map((l) => (
            <li key={l.title} className="pub-card pub-reveal">
              <h3 className="pub-h3">{l.title}</h3>
              <p>{l.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <CtaBand
        id="sec-cta"
        heading={c.help.deletion.heading}
        body={c.help.deletion.items.map((i) => i.body).join(" ")}
        primary={{ label: c.help.kicker, href: `${PUBLIC_ROUTES.help}#help-delete-title` }}
        secondary={{ label: c.about.kicker, href: PUBLIC_ROUTES.about }}
      />
      <p className="pub-note">
        <a className="pub-link" href={PUBLIC_ROUTES.platform}>
          {c.common.explorePlatform}
          <ArrowIcon />
        </a>
      </p>
    </PublicPage>
  );
}
