import React from "react";
import { WORKSPACE_PATH, moduleHref } from "../../shell/nav";
import { ArrowIcon, CtaBand, EvidenceBadges, EvidenceLegend, FaqList, ModuleMark, Section } from "../public/PublicParts";
import { localisedPublicCopy } from "../public/publicCopy";
import { requestLanguage } from "../../i18n/server";
import { PUBLIC_MODULE_IDS, platformModuleHref } from "../public/publicNav";
import { ModuleOverview } from "./ModuleOverview";

// Landing sections added in Wave 3 M3. Server Components: rendered by app/page.tsx and passed to
// the client LandingPage as slots, so their content ships no client JS. Only ModuleOverview (the
// tab switching) is client code.

const copy = async () => localisedPublicCopy(await requestLanguage());

export async function LandingCapabilities() {
  const c = await copy();
  const l = c.landing.capabilities;
  const modules = PUBLIC_MODULE_IDS.map((id) => c.modules[id]);
  const labels = modules.map((m) => (
    <React.Fragment key={m.id}>
      <ModuleMark id={m.id} />
      <span className="pub-cap-tab-text">
        <strong>{m.name}</strong>
        <span>{m.role}</span>
      </span>
    </React.Fragment>
  ));
  const panels = modules.map((m) => (
    <React.Fragment key={m.id}>
      <div className="pub-cap-panel-head">
        <ModuleMark id={m.id} size="lg" />
        <div>
          <h3>{m.name}</h3>
          <span className="pub-module-native">
            <span lang="hi">{m.native}</span> · {m.meaning} · {m.role}
          </span>
        </div>
      </div>
      <p className="pub-headline">{m.headline}</p>
      <p className="pub-section-lede">{m.lede}</p>
      <dl className="pub-cap-meta">
        <div>
          <dt>{l.checksAgainst}</dt>
          <dd>{m.against}</dd>
        </div>
        <div>
          <dt>{l.evidenceLabel}</dt>
          <dd>
            <EvidenceBadges states={m.evidence} />
          </dd>
        </div>
      </dl>
      <div className="pub-cap-links">
        <a className="pub-link" href={platformModuleHref(m.id)}>
          {l.howLink}
          <span className="sr-only">: {m.name}</span>
          <ArrowIcon />
        </a>
        <a className="pub-link" href={m.id === "kadi" ? `${WORKSPACE_PATH}#intake-dropzone` : moduleHref(m.id)}>
          {l.openLink}
          <span className="sr-only">: {m.name}</span>
          <ArrowIcon />
        </a>
      </div>
    </React.Fragment>
  ));
  return (
    <Section id="lp-capabilities" kicker={l.kicker} heading={l.heading} lede={l.lede}>
      <ModuleOverview ids={PUBLIC_MODULE_IDS} labels={labels} panels={panels} label={l.tablistLabel} />
    </Section>
  );
}

export async function LandingSteps() {
  const c = await copy();
  const l = c.landing.howItWorks;
  return (
    <Section id="lp-steps" kicker={l.kicker} heading={l.heading}>
      <ol className="pub-verbs pub-reveal">
        {c.howItWorks.stages.map((s, i) => (
          <li key={s.verb}>
            <span className="pub-num" aria-hidden="true">
              0{i + 1}
            </span>
            <strong>{s.verb}</strong>
            <span>{s.title}</span>
          </li>
        ))}
      </ol>
      <p className="pub-note">
        <a className="pub-link" href={l.link.href}>
          {l.link.label}
          <ArrowIcon />
        </a>
      </p>
    </Section>
  );
}

export async function LandingEvidence() {
  const l = (await copy()).landing.evidence;
  return (
    <Section id="lp-evidence" kicker={l.kicker} heading={l.heading} lede={l.lede}>
      <EvidenceLegend />
      <p className="pub-note">{l.note}</p>
    </Section>
  );
}

export async function LandingPrivacy() {
  const l = (await copy()).landing.privacy;
  return (
    <Section id="lp-privacy" kicker={l.kicker} heading={l.heading} lede={l.lede}>
      <ul className="pub-grid">
        {l.items.map((item, i) => (
          <li key={item.title} className="pub-card pub-reveal">
            <span className="pub-num" aria-hidden="true">
              0{i + 1}
            </span>
            <h3 className="pub-h3">{item.title}</h3>
            <p>{item.body}</p>
          </li>
        ))}
      </ul>
      <p className="pub-note">{l.disclosure}</p>
      <p className="pub-note">
        <a className="pub-link" href={l.link.href}>
          {l.link.label}
          <ArrowIcon />
        </a>
      </p>
    </Section>
  );
}

export async function LandingLanguages() {
  const l = (await copy()).landing.languages;
  return (
    <Section id="lp-languages" kicker={l.kicker} heading={l.heading} lede={l.lede}>
      <ul className="pub-grid">
        {l.items.map((item) => (
          <li key={item.title} className="pub-card pub-reveal">
            <h3 className="pub-h3">{item.title}</h3>
            <p>{item.body}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}

export async function LandingFaq() {
  const c = await copy();
  const l = c.landing.faq;
  const items = l.ids.map((id) => {
    const item = c.faq.find((f) => f.id === id);
    if (!item) throw new Error(`landing FAQ id ${id} is not in the FAQ`);
    return item;
  });
  return (
    <Section id="lp-faq" kicker={l.kicker} heading={l.heading}>
      <FaqList items={items} />
      <p className="pub-note">
        <a className="pub-link" href={l.link.href}>
          {l.link.label}
          <ArrowIcon />
        </a>
      </p>
    </Section>
  );
}

export async function LandingCta() {
  const c = await copy();
  return (
    <CtaBand
      id="lp-final"
      heading={c.landing.finalCta.heading}
      body={c.landing.finalCta.body}
      primary={c.landing.primaryCta}
      secondary={c.landing.secondaryCta}
    />
  );
}
