// The action plan shown under a module's results: situation, findings, uncertainty and next
// steps (docs/features/action-and-resolution.md). Every builder here is a pure function of one
// API response: it re-words what the server said and never adds a finding, a figure, a deadline
// or an outcome of its own. API text (reasons, remedies, labels) is passed through unchanged.
import { format, msg, type Translate } from "../i18n/format";
import type { ActionKind, ActionModule } from "../shared/api-client/accounts";
import type { AuditResponse } from "../components/modules/billnyay/types";
import type { DisputeAuditResult, GrievanceTimelineEvent } from "../components/modules/bimanyay/types";
import type { PriceCheckView } from "./dawacheck";

export type FindingGroup =
  | "needs_clarification"
  | "possible_discrepancy"
  | "missing_documentation"
  | "reference_comparison"
  | "confirmed"
  | "unable_to_assess";

export const FINDING_GROUPS: { id: FindingGroup; label: string }[] = [
  { id: "needs_clarification", label: msg("Needs clarification") },
  { id: "possible_discrepancy", label: msg("Possible discrepancy") },
  { id: "missing_documentation", label: msg("Missing documentation") },
  { id: "reference_comparison", label: msg("Reference comparison") },
  { id: "unable_to_assess", label: msg("Could not be assessed") },
  { id: "confirmed", label: msg("Checked, nothing to raise") },
];

export interface PlanFinding {
  id: string;
  group: FindingGroup;
  title: string;
  /** What was observed. */
  observed: string;
  /** What it rests on (document line, reference row, rule). */
  evidence?: string;
  /** Why the person may want to look into it. */
  why?: string;
}

export interface PlanStep {
  id: string;
  kind: ActionKind;
  title: string;
  why: string;
  prepare: string[];
  /** Only when the party to contact follows from the workflow itself. */
  contact?: string;
  /** A draft the person reads, corrects and sends themselves. */
  draft?: string;
}

export interface ActionPlanData {
  module: ActionModule;
  situation: string;
  amounts?: { label: string; value: string }[];
  findings: PlanFinding[];
  uncertainties: string[];
  steps: PlanStep[];
  whatNext: string;
}

const rupees = (n: number) => `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

export function billnyayPlan(audit: AuditResponse, tr: Translate): ActionPlanData {
  const flagged = audit.audit_items.filter((i) => i.status === "overcharged");
  const unmatched = audit.audit_items.filter((i) => i.status === "not_benchmarked");
  const findings: PlanFinding[] = audit.audit_items.map((item, index) => {
    const base = { id: `line-${index}`, title: item.item_name };
    if (item.status === "not_benchmarked")
      return {
        ...base,
        group: "unable_to_assess",
        observed: tr("Billed {charged}. This line was not compared with any reference.", { charged: rupees(item.charged) }),
        evidence: item.not_benchmarked_reason ?? tr("No matching CGHS reference row was found."),
      };
    const reference = item.cghs_benchmark === null ? "" : rupees(item.cghs_benchmark);
    const evidence = item.benchmark_basis
      ? tr("CGHS reference: {basis}", { basis: item.benchmark_basis })
      : tr("Compared with the CGHS reference rate.");
    if (item.status === "overcharged")
      return {
        ...base,
        group: "needs_clarification",
        observed: tr("Billed {charged}; the CGHS reference is {reference}.", { charged: rupees(item.charged), reference }),
        evidence,
        why: tr("It is above the government reference. A hospital may have a reason, so ask for the basis of the charge."),
      };
    if (item.status === "bundled")
      return {
        ...base,
        group: "possible_discrepancy",
        observed: tr("Billed {charged}. The audit marked this line as possibly part of another charge.", { charged: rupees(item.charged) }),
        evidence,
        why: tr("A charge already covered by a package or another line may be listed twice. Ask the hospital to confirm."),
      };
    return {
      ...base,
      group: "confirmed",
      observed: tr("Billed {charged}; not above the CGHS reference of {reference}.", { charged: rupees(item.charged), reference }),
      evidence,
    };
  });

  const toClarify = findings.filter((f) => f.group === "needs_clarification" || f.group === "possible_discrepancy").length;
  const steps: PlanStep[] = [];
  if (toClarify > 0) {
    const lines = audit.audit_items
      .filter((i) => i.status === "overcharged" || i.status === "bundled")
      .map((i) =>
        i.cghs_benchmark === null
          ? tr("- {item}: billed {charged}", { item: i.item_name, charged: rupees(i.charged) })
          : tr("- {item}: billed {charged}; CGHS reference {reference}", {
              item: i.item_name,
              charged: rupees(i.charged),
              reference: rupees(i.cghs_benchmark),
            }),
      );
    steps.push({
      id: "clarify-charges",
      kind: "clarification_request",
      title: tr("Ask the hospital to explain {count} charge(s)", { count: toClarify }),
      why: tr("A written question gets you the basis of each charge before you decide whether to dispute it."),
      prepare: [tr("Your copy of the final bill"), tr("Any package estimate or consent form you signed"), tr("The list of lines in the draft below")],
      contact: tr("The hospital's billing desk"),
      draft: [
        tr("To: The Billing Department"),
        tr("Subject: Request for clarification of charges"),
        "",
        tr("I am writing about the following lines on my bill. Please explain the basis of each charge and share an itemised breakdown."),
        "",
        ...lines,
        "",
        tr("The reference figures are CGHS rates, which I am using for comparison. I am asking for an explanation and am not alleging wrongdoing."),
        "",
        tr("Name:"),
        tr("Bill number:"),
        tr("Date:"),
      ].join("\n"),
    });
  }
  if (unmatched.length > 0)
    steps.push({
      id: "itemise-unmatched",
      kind: "collect_documents",
      title: tr("Get an itemised breakdown of {count} line(s) that could not be compared", { count: unmatched.length }),
      why: tr("Without the item name, quantity or days, a line cannot be checked either way."),
      prepare: unmatched.slice(0, 8).map((i) => i.item_name),
      contact: tr("The hospital's billing desk"),
    });

  const situation =
    toClarify > 0
      ? tr("Your bill has {count} line(s) that may need clarification. These are not confirmed overcharges.", { count: toClarify })
      : audit.benchmarked_count > 0
        ? tr("No compared line was above its CGHS reference. {count} line(s) could not be compared.", { count: audit.unmatched_count })
        : tr("No line could be compared with a CGHS reference, so nothing can be said about the prices.");

  const amounts = [{ label: tr("Amount billed (read from your document)"), value: rupees(audit.total_charged) }];
  const flaggedTotal = flagged.reduce((sum, i) => sum + i.charged, 0);
  if (flagged.length > 0) amounts.push({ label: tr("Billed on lines above the reference (to clarify)"), value: rupees(flaggedTotal) });

  return {
    module: "billnyay",
    situation,
    amounts,
    findings,
    uncertainties: [
      tr("Lines were read automatically from your document and can contain reading errors. Check them against your copy."),
      tr("CGHS rates are government reference rates. A private hospital may not be bound by them."),
      tr("Nothing here shows that money will be refunded or a charge changed."),
    ],
    steps,
    whatNext:
      steps.length > 0
        ? tr("Send the question yourself, then record the date and the reply so you know when to follow up.")
        : tr("This audit suggests no step. You can still ask the hospital about anything you do not understand."),
  };
}

export function bimanyayPlan(result: DisputeAuditResult, timeline: GrievanceTimelineEvent[], tr: Translate): ActionPlanData {
  const findings: PlanFinding[] = result.regulatory_violations.map((v, index) => ({
    id: `rule-${index}`,
    group: "possible_discrepancy",
    title: v.clause_reference,
    observed: v.violation_summary,
    evidence: v.statute_or_circular,
    why: v.legal_remedy,
  }));
  const first = timeline[0];
  const steps: PlanStep[] = [
    {
      id: "collect-denial-documents",
      kind: "collect_documents",
      title: tr("Collect the denial letter, your policy and the medical records"),
      why: tr("An appeal is judged on documents. The policy wording has not been read here, so check it yourself."),
      prepare: [tr("The insurer's denial or deduction letter"), tr("Your policy schedule and wording"), tr("Discharge summary and bills"), tr("The proposal form, if non-disclosure is alleged")],
    },
    {
      id: "grievance-level-1",
      kind: "appeal_or_grievance",
      title: first ? first.title : tr("Write to the insurer's grievance officer"),
      why: first ? first.instructions : tr("This is the first of the three drafts. It asks the insurer to review its decision."),
      prepare: [tr("The draft below, checked against your documents"), tr("Copies of the supporting documents")],
      contact: tr("The insurer's grievance redressal officer"),
      draft: result.level_1_gro_appeal,
    },
  ];
  if (result.clinical_review?.requires_clinical_interpretation)
    steps.push({
      id: "ask-treating-doctor",
      kind: "confirm_with_doctor",
      title: tr("Ask a doctor about the medical question in this denial"),
      why: result.clinical_review.note,
      prepare: result.clinical_review.suggested_clinical_question ? [result.clinical_review.suggested_clinical_question] : [],
      contact: tr("Your treating doctor"),
    });

  return {
    module: "bimanyay",
    situation: result.is_wrongful_denial
      ? tr("The rule check found points you can raise about this denial. That does not mean the insurer will change its decision.")
      : tr("The rule check found no clear rule conflict in what you entered. You can still ask the insurer to explain its decision."),
    findings,
    uncertainties: [
      tr("Your policy wording was not read, so policy clauses are not assessed."),
      tr("This rests on what you typed. Check it against the insurer's letter."),
      tr("The score is a rule-based starting estimate, not the chance that an appeal succeeds."),
    ],
    steps,
    whatNext: tr("Record when you send the grievance and what comes back. The deadlines show when the next level becomes relevant."),
  };
}

export interface MedicineResult {
  brand_name: string;
  active_ingredient: string;
  reference_entry_count: number;
  match_method?: string;
}

export function dawacheckPlan(result: MedicineResult, price: PriceCheckView, tr: Translate): ActionPlanData {
  const group: FindingGroup = price.verdict === "above" ? "needs_clarification" : price.verdict === "within" ? "confirmed" : "unable_to_assess";
  const observed = price.verdict === "cannot_compare" ? (price.reason ?? price.billed) : `${price.billed}. ${price.ceiling}.`;
  const steps: PlanStep[] = [];
  if (price.verdict === "above")
    steps.push({
      id: "ask-pharmacist",
      kind: "ask_pharmacist",
      title: tr("Ask the pharmacy about the price of {name}", { name: result.brand_name }),
      why: tr("The price per unit is above the NPPA ceiling used here. Pack size, strength or form can explain a difference."),
      prepare: [tr("The pharmacy receipt"), tr("The strip or pack, showing strength and number of units")],
      contact: tr("The pharmacy that sold it"),
      draft: [
        tr("I bought {name} ({ingredient}).", { name: result.brand_name, ingredient: result.active_ingredient }),
        `${price.billed}. ${price.ceiling}.`,
        tr("Please explain how the price was set and which ceiling price applies to this pack."),
      ].join("\n"),
    });
  if (price.verdict === "cannot_compare")
    steps.push({
      id: "check-pack",
      kind: "collect_documents",
      title: tr("Find the number of units and the strength on the pack"),
      why: tr("A comparison needs the price of one tablet, capsule or vial."),
      prepare: [tr("The strip or pack"), tr("The receipt")],
    });
  const uncertainties = [
    tr("The reference list is a curated subset of NPPA Schedule-I ({count} entries).", { count: result.reference_entry_count }),
    tr("The NPPA ceiling price is not the same thing as the printed MRP."),
  ];
  if (result.match_method === "fuzzy_phonetic") uncertainties.push(tr("The medicine was matched by spelling similarity. Confirm it is the same medicine."));
  return {
    module: "dawacheck",
    situation:
      price.verdict === "above"
        ? tr("The price you entered is above the ceiling price used for comparison. This is not a finding of wrongdoing.")
        : price.verdict === "within"
          ? tr("The price you entered is within the ceiling price used for comparison.")
          : tr("The price could not be compared, so nothing can be said about it."),
    findings: [{ id: "price", group, title: result.brand_name, observed, evidence: price.basisNote ?? undefined }],
    uncertainties,
    steps,
    whatNext: steps.length > 0 ? tr("Record the answer you get, so you have it if you ask again.") : tr("No step is suggested for this price."),
  };
}

export interface ReadinessLine {
  item_id: string;
  label: string;
  status: string;
}

export function daavisetuPlan(items: ReadinessLine[], tr: Translate): ActionPlanData {
  const groupOf: Record<string, FindingGroup> = {
    PRESENT: "confirmed",
    CONFIRMED_BY_REVIEWER: "confirmed",
    MISSING: "missing_documentation",
    NEEDS_CLINICAL_CONFIRMATION: "needs_clarification",
    REJECTED_BY_REVIEWER: "needs_clarification",
    REVIEWER_COULD_NOT_DETERMINE: "unable_to_assess",
  };
  const observedOf: Record<string, string> = {
    PRESENT: msg("Found in the text kept from your documents."),
    CONFIRMED_BY_REVIEWER: msg("Confirmed by a named reviewer."),
    MISSING: msg("Not found in the text kept from your documents."),
    NEEDS_CLINICAL_CONFIRMATION: msg("A clinical fact. A doctor needs to confirm it."),
    REJECTED_BY_REVIEWER: msg("A reviewer did not confirm this."),
    REVIEWER_COULD_NOT_DETERMINE: msg("A reviewer could not determine this from the records."),
  };
  const missing = items.filter((i) => i.status === "MISSING");
  const clinical = items.filter((i) => i.status === "NEEDS_CLINICAL_CONFIRMATION");
  const steps: PlanStep[] = [];
  if (missing.length > 0)
    steps.push({
      id: "collect-missing",
      kind: "collect_documents",
      title: tr("Collect {count} item(s) that were not found", { count: missing.length }),
      why: tr("A request with missing documents is likely to come back with questions."),
      prepare: missing.map((i) => i.label),
      contact: tr("The hospital's insurance desk"),
    });
  if (clinical.length > 0)
    steps.push({
      id: "doctor-confirms",
      kind: "confirm_with_doctor",
      title: tr("Ask the doctor to confirm {count} clinical point(s)", { count: clinical.length }),
      why: tr("Only a clinician can state a clinical fact. It is never filled in for you."),
      prepare: clinical.map((i) => i.label),
      contact: tr("Your treating doctor"),
    });
  return {
    module: "daavisetu",
    situation:
      missing.length + clinical.length > 0
        ? tr("{count} item(s) on the checklist still need attention before the package is complete.", { count: missing.length + clinical.length })
        : tr("Every checklist item was found or confirmed."),
    findings: items.map((i) => ({
      id: i.item_id,
      group: groupOf[i.status] ?? "unable_to_assess",
      title: i.label,
      observed: observedOf[i.status] ? tr(observedOf[i.status]) : i.status,
    })),
    uncertainties: [
      tr("Only the text kept from your documents was searched. A document may exist but not be recognised."),
      tr("A complete checklist does not mean the insurer will approve the request."),
    ],
    steps,
    whatNext: tr("This tool stops at a ready package. You or the hospital's insurance desk send it to the insurer."),
  };
}

export interface SchemeLine {
  scheme_name: string;
  estimated_eligibility: "eligible" | "ineligible" | "ambiguous";
  reason: string;
  claim_guide_steps: string[];
  criteria_not_evaluated: string[];
  sources: { document: string; publisher: string }[];
}

export function schemesetuPlan(results: SchemeLine[], tr: Translate): ActionPlanData {
  const open = results.filter((r) => r.estimated_eligibility !== "ineligible");
  return {
    module: "schemesetu",
    situation:
      open.length > 0
        ? tr("{count} scheme(s) may apply to you, on the criteria that were checked. This is not an eligibility decision.", { count: open.length })
        : tr("On the criteria checked, none of these schemes appears to apply. This is not an official decision."),
    findings: results.map((r, index) => ({
      id: `scheme-${index}`,
      group: r.estimated_eligibility === "ambiguous" ? "needs_clarification" : "reference_comparison",
      title: r.scheme_name,
      observed: r.reason,
      evidence: r.sources.map((s) => `${s.document} (${s.publisher})`).join("; ") || undefined,
    })),
    uncertainties: [
      ...new Set(results.flatMap((r) => r.criteria_not_evaluated)),
      tr("Only an official record or the scheme's own help desk can confirm eligibility."),
    ],
    steps: open.map((r, index) => ({
      id: `verify-${index}`,
      kind: "check_eligibility" as const,
      title: tr("Confirm {scheme} with official records", { scheme: r.scheme_name }),
      why: r.reason,
      prepare: r.claim_guide_steps,
    })),
    whatNext: tr("Record what the help desk tells you and which documents they ask for."),
  };
}

/** Re-exported for tests that check wording without a dictionary. */
export const english: Translate = (key, vars) => format(key, vars);
