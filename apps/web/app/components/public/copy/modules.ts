// English copy for the six capability pages (/platform/<id>). Every statement here was checked
// against the code named in `references[].location` or in the comment above it (2026-11-24).
// Worked examples are SYNTHETIC: made-up documents run through the real rules by hand; the
// reference figures they quote are the real rows in the repository's data files.
import { CGHS_CATEGORY_COUNTS, CGHS_TOTAL_ROWS, CGHS_VERSION, LAW_LIBRARY, NPPA_REFERENCE_FORMULATIONS } from "../../../lib/referenceSnapshot";
import { ILLUSTRATIVE_LINES, composeBill, formatINR } from "../../../lib/illustrativeBill";
import { WORKSPACE_PATH, moduleHref } from "../../../shell/nav";
import type { PublicModuleId } from "../publicNav";
import type { ModuleCopy } from "./types";

const bill = composeBill(ILLUSTRATIVE_LINES);
const line = (id: string) => {
  const l = ILLUSTRATIVE_LINES.find((x) => x.id === id);
  if (!l) throw new Error(`illustrative line ${id} missing`);
  return l;
};
const ward = line("ward");
const cbc = line("cbc");
const xray = line("xray");
const nursing = line("nursing");
const kit = line("kit");

export const MODULES_EN: Record<PublicModuleId, ModuleCopy> = {
  kadi: {
    id: "kadi",
    name: "Kadi",
    native: "कड़ी",
    meaning: "Link",
    role: "The shared document layer",
    meta: {
      title: "Kadi documents",
      description:
        "How ArogyaRakshak reads a document once, keeps only redacted, structured details, and shares them with every check in the case.",
    },
    headline: "Read once. Understood everywhere.",
    lede:
      "Kadi is not a sixth check. It is the layer every check stands on: it reads your document, pulls out the facts the checks need, removes direct identifiers from what it keeps, and discards the file.",
    against: "Your own documents",
    problem: [
      "Health paperwork arrives as phone photos, scanned PDFs and printouts, each laid out differently.",
      "Every check needs the same facts: the hospital, the diagnosis, the procedures, each bill line, the medicines, the dates. Typing them again for each check is slow and invites mistakes.",
    ],
    does: [
      "Reads the text of a PDF, or recognises the text in a scan or photo, and records how confident the recognition was for each image segment.",
      "Extracts structured details: hospital, diagnosis, procedures, bill lines with amounts, medicines and total. A language model does this when the deployment has a Groq key; otherwise local rules do.",
      "Removes direct identifiers (names, phone numbers, email addresses, Aadhaar, PAN and ABHA numbers, addresses) from the excerpt it keeps. The patient name is used in memory for the request and never stored.",
      "Links mentions of the same thing across documents (\"Dolo 650\" and \"Paracetamol 650 mg\"), and asks you when it is not sure instead of merging silently.",
      "Tells each check whether the case has enough context to run, and whether you consented to share it across checks.",
    ],
    steps: [
      { title: "You add a document", body: "PDF, JPG, PNG, WEBP, BMP, TXT or CSV, up to 10 MB. Nothing is sent until you tick the consent box." },
      { title: "Text is read", body: "PDF text layers are read directly. Scans go through text recognition, English by default; Hindi and Marathi reading is a deployment setting. Images above 8,000 pixels on a side or 40 megapixels are refused before decoding." },
      { title: "Details are extracted", body: "The text is cleaned of hidden characters and checked for prompt-injection phrasing, then turned into structured entities. A hit is disclosed, never silently acted on." },
      { title: "Identifiers are stripped, the file is dropped", body: "Only the structured details, a redacted excerpt and a SHA-256 digest of the file are stored. The file itself is never written to disk or the database." },
      { title: "Mentions are linked", body: "String similarity, Devanagari romanisation and phonetic keys decide whether two mentions are the same entity: merge, ask you, or keep apart." },
      { title: "Checks are told what they can do", body: "Each check is READY, NOT_READY (with the missing context named) or BLOCKED_NO_CONSENT." },
    ],
    inputs: [
      "Hospital bills, discharge summaries, insurer letters, prescriptions",
      "An ABDM FHIR R4 bundle you supply yourself (Patient and Practitioner resources are dropped)",
      "Your consent choice for cross-check sharing",
    ],
    outputs: [
      "Structured entities with their provenance",
      "A redacted text excerpt and the file's SHA-256 digest",
      "A case timeline and a case graph of how entities relate",
      "Readiness of each check, with what is missing",
    ],
    evidence: ["ai-generated", "rule-engine", "user-provided", "unevaluated"],
    example: {
      title: "A discharge summary becomes a case",
      intro: "A made-up two-page discharge summary, uploaded as a PDF.",
      rows: [
        { label: "Patient name", value: "Read in memory, not stored", note: "Removed from the kept excerpt" },
        { label: "Hospital", value: "Sunrise Multispeciality Hospital (made up)", evidence: "ai-generated" },
        { label: "Diagnosis", value: "Acute appendicitis", evidence: "ai-generated" },
        { label: "Procedure", value: "Laparoscopic appendectomy", evidence: "ai-generated" },
        { label: "Medicine", value: "\"Pantoprazole 40mg\" (page 1) and \"Pantoprazole 40 mg tab\" (page 2) linked as one", evidence: "rule-engine", note: "An uncertain match would be put to you instead" },
        { label: "Original PDF", value: "Discarded after reading; digest kept", evidence: "rule-engine" },
        { label: "SchemeSetu readiness", value: "NOT_READY: no income profile saved", evidence: "rule-engine" },
        { label: "DaaviSetu readiness", value: "READY, but waits for you: it never runs automatically", evidence: "rule-engine" },
      ],
      conclusion: "Every check in the case now reads these details. Nothing was uploaded twice, and the file itself no longer exists on the server.",
    },
    limitations: [
      "Text recognition is English by default. Devanagari reading must be switched on by the deployment, and handwriting is read poorly.",
      "Redaction removes direct identifiers by pattern. It is not anonymisation: a diagnosis plus a hospital name can still point to a person.",
      "When a language model is used, the first 6,000 characters of the document text go to Groq's API. Without a key, extraction is rule-based and finds less.",
      "Prompt-injection checks are heuristics. Reworded or translated attacks can get through; that is why extracted totals are cross-checked independently.",
      "Cross-lingual semantic matching (IndicSBERT) is optional and off by default. There is no vector index and no live ABDM gateway pull.",
    ],
    references: [
      { name: "Redaction rules", detail: "Labelled fields and free-standing patterns for names, phone, email, Aadhaar, PAN, ABHA, address", date: "Not a dataset; current with the code", location: "packages/kadi/kadi/privacy/redaction.py" },
      { name: "Text recognition languages", detail: "OCR_LANGUAGES setting, default English only; Hindi and Marathi supported", date: "Not a dataset", location: "packages/kadi/kadi/ocr/ocr_parser.py" },
    ],
    cta: { label: "Add a document", href: `${WORKSPACE_PATH}#intake-dropzone` },
  },

  billnyay: {
    id: "billnyay",
    name: "BillNyay",
    native: "बिल न्याय",
    meaning: "Bill justice",
    role: "Hospital bill audit",
    meta: {
      title: "BillNyay bill audit",
      description:
        "BillNyay compares each line of a hospital bill with curated CGHS reference rates, after converting units, and says plainly when a line cannot be compared.",
    },
    headline: "Every bill line, against a public reference.",
    lede:
      "BillNyay matches each line of an itemised hospital bill to a CGHS reference rate, converts the units first, and gives every line one of four answers, including \"not compared\" when there is nothing honest to compare it with.",
    against: "CGHS reference rates",
    problem: [
      "Itemised bills run to dozens of lines, priced per day, per visit, per test or per session, and give no reference point.",
      "A charge can only be called high against something. Without a reference, a patient has nothing to point to when asking a hospital to explain a bill.",
    ],
    does: [
      `Matches each bill line to the ${CGHS_TOTAL_ROWS} curated CGHS reference rows across ${CGHS_CATEGORY_COUNTS.length} categories, using names and synonyms.`,
      "Establishes the billing unit first. A per-day rate is compared only when the line states how many days; otherwise the line is not compared.",
      "Gives each line one status: above reference, within reference, usually included elsewhere (bundled), or not compared.",
      "On request, drafts an appeal letter in English, Hindi or Marathi, citing provisions that carry their own verification status, and compiles it into a PDF signed so that later changes can be detected.",
      "Also drafts a grievance, audits procedure codes and checks clinical plausibility. The dispute-outcome estimate gives no number unless a real, non-synthetic outcome dataset is registered, and none ships with this build.",
    ],
    steps: [
      { title: "Read the bill lines", body: "Kadi has already extracted each line with its quantity and amount." },
      { title: "Find a reference row", body: "Each line is matched to a CGHS row by name and synonym. No match means no comparison, never a guessed rate." },
      { title: "Convert the unit", body: "The reference is per day, visit, session, shift, bottle or service. The bill line must state a count for recurring units." },
      { title: "Decide the status", body: "Bundled rows become a question to ask; otherwise the billed amount is compared with rate × count." },
      { title: "Explain it", body: "Every finding opens a \"Why am I seeing this?\" trail with the bill line, the reference row and the rule applied." },
    ],
    inputs: ["An itemised hospital bill in the case", "Optionally: the language for the appeal letter"],
    outputs: [
      "A status and basis for every line",
      "Totals for the compared lines only",
      "An editable appeal letter and a signed PDF, with a verify check",
      "A grievance draft and procedure-code audit",
    ],
    evidence: ["external", "rule-engine", "unevaluated", "ai-generated", "verified", "provisional"],
    example: {
      title: `A ${formatINR(bill.billed)} inpatient bill`,
      intro: `A made-up bill with five lines, checked against the real ${CGHS_VERSION} rows that BillNyay uses.`,
      rows: [
        { label: `${ward.label}, ${ward.quantity}`, value: `${formatINR(ward.billed)} against ${formatINR(ward.reference ?? 0)}: above reference by ${formatINR(ward.billed - (ward.reference ?? 0))}`, evidence: "rule-engine", note: `CGHS row "${ward.rate?.name}", ${formatINR(ward.rate?.rate ?? 0)} per day` },
        { label: `${cbc.label}, ${cbc.quantity}`, value: `${formatINR(cbc.billed)} against ${formatINR(cbc.reference ?? 0)}: above reference`, evidence: "rule-engine" },
        { label: `${xray.label}, ${xray.quantity}`, value: `${formatINR(xray.billed)} against ${formatINR(xray.reference ?? 0)}: within reference`, evidence: "rule-engine" },
        { label: `${nursing.label}, ${nursing.quantity}`, value: `${formatINR(nursing.billed)}: usually included in the room charge`, evidence: "external", note: "Raised as a question, not a verdict" },
        { label: `${kit.label}, ${kit.quantity}`, value: `${formatINR(kit.billed)}: not compared, no matching row`, evidence: "unevaluated" },
      ],
      conclusion: `${formatINR(bill.aboveReference)} sits above the reference, ${formatINR(bill.bundled)} is worth asking about, and ${formatINR(bill.notCompared)} could not be checked. The tool says so instead of guessing.`,
    },
    limitations: [
      `The reference set is a curated subset: ${CGHS_TOTAL_ROWS} rows. Most lines on a real bill will be "not compared".`,
      "Each row has one rate. City class and hospital accreditation are not distinguished.",
      "A CGHS rate is a public reference point, not proof that a private hospital's charge is unlawful.",
      `Of the ${LAW_LIBRARY.total} legal provisions an appeal may cite, ${LAW_LIBRARY.verified} has been checked against a primary source. The others are marked unverified wherever they appear.`,
      "When a Groq key is configured the appeal letter is written by a language model and checked by a reviewing agent. It is a draft: read and edit it before sending.",
    ],
    references: [
      { name: "CGHS reference rates", detail: `${CGHS_TOTAL_ROWS} rows in ${CGHS_CATEGORY_COUNTS.length} categories, each with a billing unit`, date: `Version label ${CGHS_VERSION}; the file records no retrieval date`, location: "packages/billnyay/billnyay/data/cghs_rates.json" },
      { name: "Law library", detail: `${LAW_LIBRARY.total} provisions with verification status`, date: `${LAW_LIBRARY.verified} verified on 2026-09-13; ${LAW_LIBRARY.total - LAW_LIBRARY.verified} not yet verified`, location: "packages/billnyay/billnyay/data/law_library.json" },
    ],
    cta: { label: "Audit a bill", href: moduleHref("billnyay") },
  },

  daavisetu: {
    id: "daavisetu",
    name: "DaaviSetu",
    native: "दावे सेतु",
    meaning: "Claims bridge",
    role: "Cashless pre-authorisation",
    meta: {
      title: "DaaviSetu pre-authorisation",
      description:
        "DaaviSetu checks which documents a cashless pre-authorisation usually needs, fills the standard form from your case, and builds a package you submit yourself.",
    },
    headline: "Ready before the insurer asks.",
    lede:
      "DaaviSetu prepares a cashless pre-authorisation: it shows which kinds of documentation are present and which are missing, fills the form from your case, and packs it for you to submit. It ends at \"package ready\". It never submits anything and never predicts approval.",
    against: "The IRDAI standard pre-authorisation form",
    problem: [
      "A cashless request needs a form filled with details spread over several documents, often under time pressure at admission.",
      "A missing paper is usually discovered only when the insurer queries the request.",
    ],
    does: [
      "Builds a readiness checklist of the kinds of documentation commonly requested, and marks each found or missing from the case's own evidence.",
      "Keeps every clinical fact at \"needs clinical confirmation\" until a named reviewer confirms it. Software never marks a clinical fact as satisfied.",
      "Fills a pre-authorisation PDF laid out like the IRDAI standard form (Annexure-B) from the case and the policy details you enter.",
      "Compares the estimated cost with the sum insured you declare, and says nothing about the limit if you declare none.",
      "Fills your insurer's own fillable PDF if you supply it, and builds a ZIP with a manifest that lists what is not included.",
      "Lets you password-protect the PDF or ZIP in your browser before saving it.",
    ],
    steps: [
      { title: "Check readiness", body: "Each checklist item names a kind of document. Presence comes from extracted entities, or, as weaker evidence, a keyword in the redacted text." },
      { title: "Confirm clinical facts", body: "Clinical facts go to the reviewer workspace. A rejection is shown as a rejection." },
      { title: "Enter policy details", body: "Policy number, insurer and sum insured come from you; they are not in your documents." },
      { title: "Fill the form", body: "The standard-layout PDF, or your insurer's template mapped field by field." },
      { title: "Package and protect", body: "Download the PDF or ZIP, optionally encrypted with a password only you know." },
    ],
    inputs: ["The case (bills, discharge summary, reports)", "Policy details you enter", "Optionally: your insurer's fillable PDF template"],
    outputs: ["A readiness checklist with the basis of each item", "A filled pre-authorisation PDF", "A ZIP package with a manifest", "An optional encrypted copy (.arenc)"],
    evidence: ["rule-engine", "user-provided", "unevaluated", "insufficient-evidence"],
    example: {
      title: "A planned knee replacement",
      intro: "A made-up case with a doctor's estimate and two reports, before a cashless request.",
      rows: [
        { label: "Estimated cost against sum insured", value: "₹2,40,000 against ₹3,00,000: within the declared limit", evidence: "user-provided" },
        { label: "Doctor's estimate", value: "Found (extracted entities)", evidence: "rule-engine" },
        { label: "Investigation reports", value: "Found by keyword in redacted text (weaker evidence)", evidence: "rule-engine" },
        { label: "Previous treatment history", value: "Missing", evidence: "insufficient-evidence" },
        { label: "Indication for surgery", value: "Needs clinical confirmation", evidence: "unevaluated" },
        { label: "Package", value: "PDF + ZIP ready; your scanned bill is not included", evidence: "rule-engine" },
      ],
      conclusion: "You know what to collect before the insurer asks for it. Submitting the request stays with you and the hospital desk.",
    },
    limitations: [
      "Nothing is sent to an insurer or TPA. There is no insurer integration.",
      "No real insurer's proprietary template ships with the project; the filler works on a fillable PDF you supply.",
      "The package never contains your original documents, because they are not kept. The manifest tells you to attach them yourself.",
      "Readiness is completeness, not approval. Nothing here predicts or improves the chance of approval.",
      "Password protection covers DaaviSetu downloads only, on the web only. A forgotten password cannot be recovered.",
    ],
    references: [
      { name: "Pre-authorisation form layout", detail: "Annexure-B of the IRDAI guidelines on standardisation of health insurance claims, as laid out by the generator", date: "The generator records no form version date", location: "packages/daavisetu/daavisetu/generator.py" },
      { name: "Readiness playbooks", detail: "Checklists of commonly requested documentation, versioned and activated by an institution", date: "Versioned per playbook", location: "packages/daavisetu/daavisetu/readiness.py" },
    ],
    cta: { label: "Prepare a request", href: moduleHref("daavisetu") },
  },

  bimanyay: {
    id: "bimanyay",
    name: "BimaNyay",
    native: "बीमा न्याय",
    meaning: "Insurance justice",
    role: "Claim denial review",
    meta: {
      title: "BimaNyay claim denials",
      description:
        "BimaNyay reads a claim denial against IRDAI rules, drafts the grievance, portal summary and Ombudsman statement, and computes the escalation deadlines.",
    },
    headline: "A denial is not the last word.",
    lede:
      "BimaNyay checks the stated reason for a rejected or reduced claim against IRDAI rules, drafts the three escalation documents from templates, and works out the deadlines for each step.",
    against: "IRDAI rules and timelines",
    problem: [
      "Denial letters cite clauses and categories that are hard to check from the outside.",
      "Each escalation step, from the insurer's grievance officer to the Ombudsman, has its own deadline. Missing one can close the route.",
    ],
    does: [
      "Checks four common denial grounds: pre-existing disease (including the five-year moratorium), investigation-only admission, room-rent proportionate deduction and delayed intimation.",
      "Drafts a letter to the insurer's Grievance Redressal Officer, a summary of up to 2,000 characters for the Bima Bharosa portal, and an Ombudsman statement. These are templates, not language-model output.",
      "Writes the drafts in English, Hindi or Marathi.",
      "Computes the deadlines: 15 days for the grievance officer, 15 more for the Bima Bharosa review, and one year for an Ombudsman complaint, in calendar days.",
    ],
    steps: [
      { title: "Describe the denial", body: "The category, the policy age and the diagnosis, from the letter or typed by you." },
      { title: "Check the ground", body: "A deterministic rule decides whether the ground is contestable and which provision it cites." },
      { title: "Draft three tiers", body: "Grievance officer, Bima Bharosa and Ombudsman, ready to edit." },
      { title: "Track the clock", body: "Each deadline is shown with the rule and the dates it was computed from." },
    ],
    inputs: ["Denial category and date", "Policy age in years", "Diagnosis", "Optionally: the case, if the denial belongs to one"],
    outputs: ["Grounds with cited provisions", "Three draft documents", "A deadline timeline with explanations"],
    evidence: ["rule-engine", "external", "provisional", "user-provided"],
    example: {
      title: "A pre-existing-disease denial",
      intro: "A made-up rejection citing non-disclosure of a pre-existing disease, on a policy renewed for six continuous years. Dispute started 5 January 2026.",
      rows: [
        { label: "Ground", value: "Five-year moratorium applies (policy age 6 years)", evidence: "rule-engine" },
        { label: "Cited provision", value: "IRDAI Master Circular on health insurance, 29 May 2024", evidence: "external" },
        { label: "Grievance officer deadline", value: "20 January 2026 (start + 15 days)", evidence: "rule-engine" },
        { label: "Bima Bharosa review window", value: "4 February 2026 (+15 days)", evidence: "rule-engine" },
        { label: "Ombudsman limitation", value: "5 January 2027 (start + 365 days)", evidence: "rule-engine" },
      ],
      conclusion: "You have the grounds, three drafts and the dates in one place. Sending each letter is your decision.",
    },
    limitations: [
      "Only four denial grounds have specific rules. Anything else gets a general ground.",
      "No IRDAI provision backing the room-rent proportionate-deduction ground has been verified against a primary source yet; the code says so.",
      "Deadlines are calendar days. Holidays and working-day rules are not applied.",
      "The Hindi and Marathi wording of grounds and drafts has not been reviewed by a native speaker.",
      "Nothing is filed for you. The drafts are starting points to check and edit.",
    ],
    references: [
      { name: "IRDAI Master Circular", detail: "IRDAI/HLT/CIR/PRO/84/5/2024: moratorium and claim-handling rules", date: "Issued 29 May 2024", location: "packages/bimanyay/bimanyay/clause_auditor.py" },
      { name: "Insurance Ombudsman Rules, 2017", detail: "Rule 14(3)(b): one-year limitation", date: "Verified 2026-09-13 against the consolidated text", location: "packages/bimanyay/bimanyay/tracker.py" },
    ],
    cta: { label: "Review a denial", href: moduleHref("bimanyay") },
  },

  schemesetu: {
    id: "schemesetu",
    name: "SchemeSetu",
    native: "योजना सेतु",
    meaning: "Scheme bridge",
    role: "Government scheme eligibility",
    meta: {
      title: "SchemeSetu scheme eligibility",
      description:
        "SchemeSetu gives a provisional, cited reading of PM-JAY and MJPJAY eligibility, criterion by criterion, without inventing income limits.",
    },
    headline: "Eligibility, criterion by criterion.",
    lede:
      "SchemeSetu applies the published criteria of two schemes, PM-JAY and Maharashtra's MJPJAY, to what you tell it, shows each step of the reasoning with its source, and calls every result provisional.",
    against: "PM-JAY and MJPJAY published criteria",
    problem: [
      "Scheme rules have changed several times, and income limits quoted widely are not in the official sources.",
      "Families need to know what to check and whom to ask before a hospital admission, not after it.",
    ],
    does: [
      "Applies deterministic rules and reports each scheme as eligible or ambiguous. Only your stated state of residence decides anything: MJPJAY covers every family in Maharashtra, while PM-JAY's criteria (SECC-2011 or state database listing, ASHA and Anganwadi families, age 70 and over) are not collected, so PM-JAY is always ambiguous.",
      "Records income, social category and medical need, and reports them as not evaluated: neither scheme defines an annual income ceiling in the cited sources, and category and need are not criteria in them.",
      "Shows a step-by-step reasoning trace. Each sentence carries a citation status, mapped to an evidence badge.",
      "Explains what changes when a family moves between PM-JAY and MJPJAY, and keeps an income profile on the case only if you save one; you can delete it.",
    ],
    steps: [
      { title: "Tell it the basics", body: "State of residence (a Maharashtra city name or a Devanagari spelling is recognised), income, social category and medical need." },
      { title: "Apply the criteria", body: "From one source of truth with citations and their retrieval date." },
      { title: "Show the reasoning", body: "Criterion by criterion, with what was checked and what could not be." },
      { title: "Point to the next step", body: "How to claim where the reading is eligible; how to verify where it is ambiguous." },
    ],
    inputs: ["State of residence (decides)", "Annual income (recorded, not decisive)", "Social category (recorded)", "Medical need (recorded)"],
    outputs: ["A provisional reading per scheme", "The reasoning trace with citation statuses", "Steps to claim or verify", "Official sources with dates"],
    evidence: ["provisional", "verified", "unevaluated", "external", "user-provided"],
    example: {
      title: "A family in Pune",
      intro: "Made-up inputs: state typed as \"Pune\", general category, annual income ₹1,80,000, planned knee surgery.",
      rows: [
        { label: "State", value: "\"Pune\" interpreted as Maharashtra (city name)", evidence: "rule-engine", note: "Residence is not verified against documents" },
        { label: "MJPJAY", value: "Eligible (provisional): the scheme covers all families in Maharashtra", evidence: "provisional" },
        { label: "PM-JAY", value: "Ambiguous: needs SECC-2011 or state database listing, which is not collected", evidence: "unevaluated" },
        { label: "Income ₹1,80,000", value: "Recorded, not used to decide", evidence: "user-provided" },
        { label: "Next step", value: "Ask the Arogya Mitra desk at an empanelled hospital", evidence: "external" },
      ],
      conclusion: "The family knows which scheme to ask about first and what proof the desk will want. No official decision is implied.",
    },
    limitations: [
      "Every result is provisional. It is not an official eligibility decision.",
      "Only two schemes are covered: PM-JAY and MJPJAY.",
      "PM-JAY is always reported as needing verification, because its listing criteria are not collected.",
      "The MJPJAY order itself (GR of 28 July 2023) could not be retrieved; the citations are Government of Maharashtra portals that restate it.",
      "There is no empanelled-hospital directory.",
    ],
    references: [
      { name: "PM-JAY criteria", detail: "PIB releases 2116209 and 2053883", date: "Released 28 Mar 2025 and 11 Sep 2024; retrieved 2026-09-13", location: "packages/schemesetu/schemesetu/thresholds.py" },
      { name: "MJPJAY criteria", detail: "Government of Maharashtra portals restating the GR of 28 July 2023", date: "Retrieved 2026-09-13", location: "packages/schemesetu/schemesetu/thresholds.py" },
    ],
    cta: { label: "Check eligibility", href: moduleHref("schemesetu") },
  },

  dawacheck: {
    id: "dawacheck",
    name: "DawaCheck",
    native: "दवा चेक",
    meaning: "Medicine check",
    role: "Medicine ceiling prices",
    meta: {
      title: "DawaCheck medicine prices",
      description:
        "DawaCheck compares what you paid for a medicine with its NPPA ceiling price, but only after working out the price per tablet, capsule or vial.",
    },
    headline: "Price per tablet, not per guess.",
    lede:
      "DawaCheck compares the price of a medicine with its NPPA ceiling price. It first works out what the amount actually buys, one tablet, a strip or a whole line, and refuses to compare when the bill does not say.",
    against: "NPPA ceiling prices",
    problem: [
      "Ceiling prices are set per tablet, capsule or vial. Bills show strip, pack or line totals.",
      "Comparing a strip price with a per-tablet ceiling produces absurd results: in this project's own early tests, a ₹33 strip of fifteen showed up as 1,335% over the ceiling.",
    ],
    does: [
      `Resolves a brand name to a formulation in its curated subset of ${NPPA_REFERENCE_FORMULATIONS} NPPA Schedule-I formulations, using aliases, phonetic matching and dosage normalisation.`,
      "Establishes the price basis (per unit, per strip, per pack or line total) from your declaration or from what the document states, and converts to a price per unit only when the number of units is stated.",
      "Otherwise reports \"cannot compare\" with a plain reason.",
      "Checks the medicines Kadi extracted from a case, or one you type in, and expands prescription shorthand (TDS, BD, HS) into plain language.",
    ],
    steps: [
      { title: "Find the formulation", body: "Brand to active ingredient and strength, or \"not in the reference list\"." },
      { title: "Establish the basis", body: "What did the amount buy: one unit, a strip of N, a pack, a line?" },
      { title: "Convert or refuse", body: "Per-unit price only when the count is stated. Contradictions mean no comparison." },
      { title: "Compare", body: "Per-unit price against the per-unit ceiling, with the basis shown." },
    ],
    inputs: ["Medicine name as written", "Amount paid", "What the amount covers (unit, strip, pack, line)"],
    outputs: ["A price per unit, or a reason it cannot be computed", "The ceiling price and the comparison", "The data source and how many entries it has"],
    evidence: ["external", "rule-engine", "user-provided", "unevaluated"],
    example: {
      title: "A strip of paracetamol",
      intro: "A made-up receipt line: \"Dolo 650, strip of 15, ₹33\".",
      rows: [
        { label: "Formulation", value: "Paracetamol 650 mg (alias \"Dolo 650\")", evidence: "rule-engine" },
        { label: "Price basis", value: "Per strip of 15, stated on the line", evidence: "user-provided" },
        { label: "Price per tablet", value: "₹33 ÷ 15 = ₹2.20", evidence: "rule-engine" },
        { label: "NPPA ceiling", value: "₹2.30 per tablet", evidence: "external" },
        { label: "Result", value: "Within the ceiling", evidence: "rule-engine" },
      ],
      conclusion: "Compared per tablet, the price is within the ceiling. Compared per strip, it would have looked fifteen times too high.",
    },
    limitations: [
      `The reference list has ${NPPA_REFERENCE_FORMULATIONS} formulations. A medicine missing from it is not necessarily uncontrolled.`,
      "The reference file records no NPPA notification date, and ceiling prices change by notification.",
      "Generic alternatives come from notes in the same curated data, not from a live Jan Aushadhi catalogue.",
      "Shorthand expansion covers a small fixed set of abbreviations; anything else is left as written.",
    ],
    references: [
      { name: "NPPA Schedule-I (curated subset)", detail: `${NPPA_REFERENCE_FORMULATIONS} formulations with per-unit ceiling prices and brand aliases`, date: "No notification or retrieval date recorded in the file", location: "packages/dawacheck/dawacheck/reference_data.py" },
      { name: "Price basis rules", detail: "Per unit, strip, pack and line-total conversion; refuses to guess", date: "Not a dataset (ADR-012)", location: "packages/dawacheck/dawacheck/price_basis.py" },
    ],
    cta: { label: "Check a medicine", href: moduleHref("dawacheck") },
  },
};
