"use client";

// One entry point per module, so a view loads the plan builders and the panel only when it has a
// result to explain (next/dynamic keeps them out of the route's initial JavaScript).
import React from "react";
import { useT } from "../../i18n/useT";
import {
  billnyayPlan,
  bimanyayPlan,
  daavisetuPlan,
  dawacheckPlan,
  schemesetuPlan,
  type MedicineResult,
  type ReadinessLine,
  type SchemeLine,
} from "../../lib/actionPlan";
import { describePriceCheck, type PriceCheck } from "../../lib/dawacheck";
import type { AuditResponse } from "../modules/billnyay/types";
import type { DisputeAuditResult, GrievanceTimelineEvent } from "../modules/bimanyay/types";
import { ActionPlan } from "./ActionPlan";

export type ModulePlanProps = { caseId?: string } & (
  | { module: "billnyay"; audit: AuditResponse }
  | { module: "bimanyay"; result: DisputeAuditResult; timeline: GrievanceTimelineEvent[] }
  | { module: "dawacheck"; result: MedicineResult & PriceCheck }
  | { module: "daavisetu"; items: ReadinessLine[] }
  | { module: "schemesetu"; results: SchemeLine[] }
);

export function ModulePlan(props: ModulePlanProps) {
  const tr = useT();
  const plan =
    props.module === "billnyay"
      ? billnyayPlan(props.audit, tr)
      : props.module === "bimanyay"
        ? bimanyayPlan(props.result, props.timeline, tr)
        : props.module === "dawacheck"
          ? dawacheckPlan(props.result, describePriceCheck(props.result, tr), tr)
          : props.module === "daavisetu"
            ? daavisetuPlan(props.items, tr)
            : schemesetuPlan(props.results, tr);
  return <ActionPlan plan={plan} caseId={props.caseId || undefined} />;
}
