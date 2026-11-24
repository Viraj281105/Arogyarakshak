// Shapes of the public-site copy (Wave 3 M3). Plain strings only, so the pages stay Server
// Components and the copy never enters a client bundle (client parts receive strings as props).
import type { EvidenceState } from "../../ui/evidence";
import type { PublicModuleId } from "../publicNav";

export interface Link {
  label: string;
  href: string;
}

export interface TitledText {
  title: string;
  body: string;
}

/** A control or fact with the place in the repository it can be checked against. */
export interface SourcedFact extends TitledText {
  source: string;
}

export interface PageMeta {
  /** <title> (the site name is appended by the page). */
  title: string;
  description: string;
}

export interface FaqItem {
  id: string;
  question: string;
  answer: string[];
  /** Topic used for the help page filter chips. */
  topic: "basics" | "privacy" | "accounts" | "findings" | "modules";
  /** Extra words matched by the help search (synonyms, module names). */
  keywords: string;
}

export interface ReferenceSource {
  name: string;
  detail: string;
  /** What the repository records about the date of this data; never guessed. */
  date: string;
  /** Where in the repository the data or rule lives. */
  location: string;
}

export interface ExampleRow {
  label: string;
  value: string;
  evidence?: EvidenceState;
  note?: string;
}

export interface ModuleCopy {
  id: PublicModuleId;
  name: string;
  /** Name in Devanagari and its literal meaning. */
  native: string;
  meaning: string;
  /** One-line role, e.g. "Hospital bill audit". */
  role: string;
  meta: PageMeta;
  headline: string;
  lede: string;
  /** "Checks against …" line for cards. */
  against: string;
  problem: string[];
  does: string[];
  steps: TitledText[];
  inputs: string[];
  outputs: string[];
  /** Evidence states this capability's results can carry. */
  evidence: EvidenceState[];
  example: {
    title: string;
    intro: string;
    rows: ExampleRow[];
    conclusion: string;
  };
  limitations: string[];
  references: ReferenceSource[];
  cta: Link;
}

export interface PublicCopy {
  /** "reviewed" only for English. Hindi and Marathi stay "pending" until a native speaker writes them. */
  translation: "source" | "pending";
  siteName: string;
  common: {
    synthetic: string;
    syntheticNote: string;
    openWorkspace: string;
    checkDocument: string;
    explorePlatform: string;
    learnMore: string;
    sourcePrefix: string;
    breadcrumbHome: string;
  };
  landing: {
    meta: PageMeta;
    eyebrow: string;
    headlineLead: string;
    headlineEmphasis: string;
    lede: string;
    primaryCta: Link;
    secondaryCta: Link;
    assurances: TitledText[];
    reviewerNote: string;
    reviewerLink: Link;
    figureCaption: string;
    capabilities: { kicker: string; heading: string; lede: string; tablistLabel: string; checksAgainst: string; evidenceLabel: string; howLink: string; openLink: string };
    howItWorks: { kicker: string; heading: string; link: Link };
    evidence: { kicker: string; heading: string; lede: string; note: string };
    privacy: { kicker: string; heading: string; lede: string; items: TitledText[]; disclosure: string; link: Link };
    languages: { kicker: string; heading: string; lede: string; items: TitledText[] };
    faq: { kicker: string; heading: string; ids: string[]; link: Link };
    finalCta: { heading: string; body: string };
  };
  platform: {
    meta: PageMeta;
    kicker: string;
    headline: string;
    lede: string;
    ecosystem: { kicker: string; heading: string; lede: string; hubLabel: string; hubBody: string };
    kadi: { kicker: string; heading: string; lede: string; items: TitledText[]; link: Link };
    context: {
      kicker: string;
      heading: string;
      lede: string[];
      states: { state: string; meaning: string }[];
      statesCaption: string;
      notes: string[];
    };
    evidence: { kicker: string; heading: string; lede: string; provenanceHeading: string; provenance: TitledText[] };
    access: {
      kicker: string;
      heading: string;
      lede: string;
      columns: [string, string, string];
      rows: { aspect: string; guest: string; account: string }[];
      caption: string;
      note: string;
    };
    review: { heading: string; body: string; link: Link };
    modulesHeading: string;
  };
  howItWorks: {
    meta: PageMeta;
    kicker: string;
    headline: string;
    lede: string;
    stages: { verb: string; title: string; body: string; kept: string; evidence: EvidenceState[] }[];
    keptLabel: string;
    evidenceLabel: string;
    sharing: { kicker: string; heading: string; lede: string; steps: TitledText[] };
    control: { kicker: string; heading: string; items: TitledText[] };
  };
  security: {
    meta: PageMeta;
    kicker: string;
    headline: string;
    lede: string;
    controlsHeading: string;
    controls: SourcedFact[];
    flowHeading: string;
    flowLede: string;
    flow: { what: string; where: string; when: string }[];
    flowColumns: [string, string, string];
    limitsHeading: string;
    limitsLede: string;
    limits: TitledText[];
  };
  about: {
    meta: PageMeta;
    kicker: string;
    headline: string;
    lede: string;
    mission: { heading: string; body: string[] };
    principlesHeading: string;
    principles: TitledText[];
    names: { heading: string; lede: string };
    isNot: { heading: string; items: string[] };
    built: { heading: string; items: TitledText[] };
  };
  help: {
    meta: PageMeta;
    kicker: string;
    headline: string;
    lede: string;
    search: { label: string; placeholder: string; all: string; empty: string; count: string; topics: Record<FaqItem["topic"], string> };
    faqHeading: string;
    guidesHeading: string;
    guidesLede: string;
    guides: { id: PublicModuleId; ready: string[]; where: string }[];
    guideReady: string;
    guideWhere: string;
    deletion: { heading: string; items: TitledText[] };
  };
  faq: FaqItem[];
  modules: Record<PublicModuleId, ModuleCopy>;
  moduleSections: {
    problem: string;
    does: string;
    how: string;
    inputs: string;
    outputs: string;
    evidence: string;
    example: string;
    limitations: string;
    references: string;
    referenceDate: string;
    referenceLocation: string;
    others: string;
    breadcrumbPlatform: string;
  };
}
