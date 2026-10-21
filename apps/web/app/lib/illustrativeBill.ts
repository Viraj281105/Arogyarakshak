/**
 * The made-up bill the landing page walks through. It is not a patient's bill: the billed
 * amounts are invented, the reference rates are the real CGHS rows shipped with BillNyay, and
 * each line's status follows the same rule as apps/api/app/services/billnyay_audit.py —
 * no matching row → not benchmarked; a bundled row → bundled; charged above the reference
 * total → overcharged; otherwise within benchmark.
 */

import { CGHS_EXAMPLE_RATES, CghsRate } from "./referenceSnapshot";

export type LineStatus = "overcharged" | "within_benchmark" | "bundled" | "not_benchmarked";

export interface IllustrativeLine {
  id: string;
  label: string;
  quantity: string;
  billed: number;
  /** The reference total for this line (rate × count), or null when no row matched. */
  reference: number | null;
  rate: CghsRate | null;
  status: LineStatus;
}

interface RawLine {
  id: string;
  label: string;
  quantity: string;
  count: number;
  billed: number;
  rate: CghsRate | null;
}

const RAW: RawLine[] = [
  { id: "ward", label: "General ward bed", quantity: "3 days × ₹2,400", count: 3, billed: 7200, rate: CGHS_EXAMPLE_RATES.ward },
  { id: "nursing", label: "Routine nursing", quantity: "3 days × ₹600", count: 3, billed: 1800, rate: CGHS_EXAMPLE_RATES.nursing },
  { id: "cbc", label: "Complete blood count", quantity: "1 test", count: 1, billed: 600, rate: CGHS_EXAMPLE_RATES.bloodTest },
  { id: "xray", label: "Chest X-ray", quantity: "1 film", count: 1, billed: 350, rate: CGHS_EXAMPLE_RATES.xray },
  { id: "kit", label: "Admission kit", quantity: "1 kit", count: 1, billed: 1200, rate: null },
];

function statusOf(line: RawLine, reference: number | null): LineStatus {
  if (reference === null || !line.rate) return "not_benchmarked";
  if (line.rate.bundled) return "bundled";
  return line.billed > reference ? "overcharged" : "within_benchmark";
}

export const ILLUSTRATIVE_LINES: IllustrativeLine[] = RAW.map((line) => {
  const reference = line.rate ? line.rate.rate * line.count : null;
  return {
    id: line.id,
    label: line.label,
    quantity: line.quantity,
    billed: line.billed,
    reference,
    rate: line.rate,
    status: statusOf(line, reference),
  };
});

export interface BillComposition {
  billed: number;
  /** Charged amount up to the reference on compared lines. */
  withinReference: number;
  /** Charged amount above the reference on compared lines. */
  aboveReference: number;
  /** Charged for items the reference says belong inside another charge. */
  bundled: number;
  /** Charged for lines with no reference row: not checked either way. */
  notCompared: number;
}

export function composeBill(lines: IllustrativeLine[]): BillComposition {
  const c: BillComposition = { billed: 0, withinReference: 0, aboveReference: 0, bundled: 0, notCompared: 0 };
  for (const l of lines) {
    c.billed += l.billed;
    if (l.status === "not_benchmarked") c.notCompared += l.billed;
    else if (l.status === "bundled") c.bundled += l.billed;
    else {
      const ref = l.reference ?? 0;
      c.withinReference += Math.min(l.billed, ref);
      c.aboveReference += Math.max(0, l.billed - ref);
    }
  }
  return c;
}

export const formatINR = (n: number) => `₹${n.toLocaleString("en-IN")}`;
