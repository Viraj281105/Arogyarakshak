import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ArrowIcon, CtaBand, EvidenceBadge, EvidenceLegend, ModuleCard, ModuleMark, PublicHero, PublicPage, Section } from "../../components/public/PublicParts";
import { localisedPublicCopy, pageTitle } from "../../components/public/publicCopy";
import { PUBLIC_MODULE_IDS, PUBLIC_ROUTES, type PublicModuleId } from "../../components/public/publicNav";
import { requestLanguage } from "../../i18n/server";

/** One statically generated page per capability; any other segment is a 404. */
export const dynamicParams = false;

export function generateStaticParams(): { module: PublicModuleId }[] {
  return PUBLIC_MODULE_IDS.map((module) => ({ module }));
}

function isModule(id: string): id is PublicModuleId {
  return (PUBLIC_MODULE_IDS as readonly string[]).includes(id);
}

export async function generateMetadata({ params }: { params: Promise<{ module: string }> }): Promise<Metadata> {
  const { module } = await params;
  if (!isModule(module)) return {};
  const m = (await localisedPublicCopy(await requestLanguage())).modules[module];
  return { title: pageTitle(m.meta.title), description: m.meta.description };
}

/** /platform/<id> (Server Component): problem, workflow, inputs and outputs, a synthetic example, limits, data. */
export default async function ModulePage({ params }: { params: Promise<{ module: string }> }) {
  const { module } = await params;
  if (!isModule(module)) notFound();
  const c = await localisedPublicCopy(await requestLanguage());
  const m = c.modules[module];
  const s = c.moduleSections;
  const id = `mod-${m.id}`;

  return (
    <PublicPage module={m.id}>
      <PublicHero
        kicker={`${m.name} · ${m.role}`}
        title={m.headline}
        lede={m.lede}
        breadcrumbs={[
          { label: c.common.breadcrumbHome, href: "/" },
          { label: s.breadcrumbPlatform, href: PUBLIC_ROUTES.platform },
          { label: m.name },
        ]}
        actions={
          <>
            <a className="btn btn-primary btn-lg" href={m.cta.href}>
              {m.cta.label}
              <ArrowIcon size={18} />
            </a>
            <a className="btn btn-ghost btn-lg" href={`#${id}-example`}>
              {s.example}
            </a>
          </>
        }
        aside={
          <div className="pub-signature">
            <ModuleMark id={m.id} size="lg" />
            <span className="pub-signature-native" lang="hi">
              {m.native}
            </span>
            <p>“{m.meaning}”</p>
            <dl>
              <div>
                <dt>{c.landing.capabilities.checksAgainst}</dt>
                <dd>{m.against}</dd>
              </div>
            </dl>
          </div>
        }
      />

      <Section id={`${id}-problem`} kicker={s.problem} heading={m.problem[0]}>
        <div className="pub-split">
          <div className="pub-prose pub-reveal">
            {m.problem.slice(1).map((t) => (
              <p key={t}>{t}</p>
            ))}
          </div>
          <div className="pub-reveal">
            <h3 className="pub-h3">{s.does}</h3>
            <ul className="pub-list">
              {m.does.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
        </div>
      </Section>

      <Section id={`${id}-how`} kicker={m.name} heading={s.how}>
        <div className="pub-split">
          <ol className="pub-steps pub-reveal">
            {m.steps.map((step) => (
              <li key={step.title} className="pub-step">
                <div>
                  <h3 className="pub-h3">{step.title}</h3>
                  <p>{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
          <div className="pub-io pub-reveal">
            <div className="pub-card">
              <h3 className="pub-h3">{s.inputs}</h3>
              <ul className="pub-list">
                {m.inputs.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </div>
            <div className="pub-card">
              <h3 className="pub-h3">{s.outputs}</h3>
              <ul className="pub-list">
                {m.outputs.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </Section>

      <section className="pub-section" id={`${id}-example`} aria-labelledby={`${id}-example-title`}>
        <div className="pub-section-head pub-reveal">
          <p className="pub-kicker">{s.example}</p>
          <h2 id={`${id}-example-title`} className="pub-h2">
            {m.example.title}
          </h2>
        </div>
        <figure className="pub-example pub-reveal" aria-labelledby={`${id}-example-title`}>
          <div className="pub-example-head">
            <div>
              <span className="pub-synthetic">{c.common.synthetic}</span>
              <p>{m.example.intro}</p>
            </div>
          </div>
          <ul className="pub-example-rows">
            {m.example.rows.map((r) => (
              <li key={r.label}>
                <span className="pub-example-label">{r.label}</span>
                <span className="pub-example-value">
                  {r.value}
                  {r.note && <small>{r.note}</small>}
                </span>
                <span>{r.evidence && <EvidenceBadge state={r.evidence} size="sm" />}</span>
              </li>
            ))}
          </ul>
          <p className="pub-example-conclusion">{m.example.conclusion}</p>
          <figcaption className="pub-example-foot">{c.common.syntheticNote}</figcaption>
        </figure>
      </section>

      <Section id={`${id}-evidence`} kicker={m.name} heading={s.evidence}>
        <EvidenceLegend states={m.evidence} />
      </Section>

      <Section id={`${id}-limits`} kicker={m.name} heading={s.limitations}>
        <ul className="pub-list pub-list-limits pub-reveal">
          {m.limitations.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      </Section>

      <Section id={`${id}-data`} kicker={m.name} heading={s.references}>
        <ul className="pub-grid pub-grid-2">
          {m.references.map((r) => (
            <li key={r.name} className="pub-card pub-card-accent pub-reveal">
              <h3 className="pub-h3">{r.name}</h3>
              <p>{r.detail}</p>
              <dl className="pub-facts">
                <div>
                  <dt>{s.referenceDate}</dt>
                  <dd>{r.date}</dd>
                </div>
                <div>
                  <dt>{s.referenceLocation}</dt>
                  <dd>
                    <span className="pub-code">{r.location}</span>
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      </Section>

      <CtaBand id={`${id}-cta`} heading={m.headline} body={m.lede} primary={m.cta} secondary={{ label: s.breadcrumbPlatform, href: PUBLIC_ROUTES.platform }} />

      <Section id={`${id}-others`} heading={s.others}>
        <ul className="pub-grid">
          {PUBLIC_MODULE_IDS.filter((other) => other !== m.id).map((other) => (
            <li key={other} className="pub-reveal">
              <ModuleCard module={c.modules[other]} linkLabel={c.common.learnMore} />
            </li>
          ))}
        </ul>
      </Section>
    </PublicPage>
  );
}
