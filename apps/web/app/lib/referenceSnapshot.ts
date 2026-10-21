/**
 * What the reference data shipped in this build actually contains, for the landing page.
 *
 * The web app cannot import the Python packages' data files, so the figures are copied here
 * and `tests/reference_snapshot.test.ts` fails as soon as they drift from
 * packages/billnyay/billnyay/data/*.json or packages/dawacheck/dawacheck/reference_data.py.
 * Nothing on the landing page may state a reference count that is not in this file.
 */

export interface CghsRate {
  key: string;
  name: string;
  rate: number;
  unit: "per_day" | "per_visit" | "per_session" | "per_shift" | "per_bottle" | "per_service";
  bundled: boolean;
}

export const CGHS_VERSION = "CGHS-2024-REVISED";

/** Rows of cghs_rates.json per category, largest first. */
export const CGHS_CATEGORY_COUNTS: ReadonlyArray<{ category: string; rows: number }> = [
  { category: "Room Tariff", rows: 4 },
  { category: "Cardiology", rows: 3 },
  { category: "Consultation", rows: 2 },
  { category: "Room & Critical Care", rows: 2 },
  { category: "Equipment", rows: 2 },
  { category: "Consumables", rows: 2 },
  { category: "Diagnostics", rows: 2 },
  { category: "Radiology", rows: 2 },
  { category: "Surgical", rows: 2 },
  { category: "Nursing", rows: 1 },
  { category: "Pharmacy", rows: 1 },
  { category: "Pathology", rows: 1 },
  { category: "Orthopedics", rows: 1 },
  { category: "Ophthalmology", rows: 1 },
  { category: "Nephrology", rows: 1 },
];

export const CGHS_TOTAL_ROWS = CGHS_CATEGORY_COUNTS.reduce((sum, c) => sum + c.rows, 0);

/** The CGHS rows the illustrative bill on the landing page is checked against. */
export const CGHS_EXAMPLE_RATES: Record<"ward" | "bloodTest" | "xray" | "nursing", CghsRate> = {
  ward: { key: "ward stay", name: "General Ward Bed Charges", rate: 1500, unit: "per_day", bundled: false },
  bloodTest: { key: "blood test", name: "Complete Blood Count (CBC) / Routine Panel", rate: 250, unit: "per_service", bundled: false },
  xray: { key: "x-ray", name: "Chest / General Digital X-Ray", rate: 350, unit: "per_service", bundled: false },
  nursing: { key: "nursing charges", name: "Routine Nursing Charges", rate: 0, unit: "per_day", bundled: true },
};

/** law_library.json: provisions the appeal drafts may cite, by verification status. */
export const LAW_LIBRARY = { total: 5, verified: 1 } as const;

/** dawacheck/reference_data.py: NPPA_REFERENCE_DATA entries (a curated subset). */
export const NPPA_REFERENCE_FORMULATIONS = 7;

/** SchemeSetu evaluates these two schemes' published rules. */
export const SCHEMES = ["PM-JAY", "MJPJAY"] as const;
