/** DawaCheck: NPPA benchmark and prescription translation types. Mirrors the FastAPI schemas in apps/api. */
import type { Explanation } from '../../services/explanation';
import type { Provenance } from './clinical';

// --- DawaCheck ---
export interface DawaCheckBenchmarkRequest {
  brand_name: string;
  /** The amount paid, on the basis in `price_basis`. */
  mrp: number;
  price_basis?: 'PER_UNIT' | 'PER_STRIP' | 'PER_PACK' | 'LINE_TOTAL' | 'UNKNOWN';
  units_per_pack?: number;
  quantity?: number;
}

export interface DawaCheckBenchmarkResponse {
  brand_name: string;
  active_ingredient: string;
  /** Amount as billed/entered (see price_basis); the per-unit figure is billed_unit_price. */
  mrp: number;
  /** Ceiling per unit_label (one tablet/capsule/vial). */
  nppa_ceiling_price: number;
  /** null when no comparison could be made (comparison_status CANNOT_COMPARE). */
  is_overcharged: boolean | null;
  deviation_percentage: number | null;
  comparison_status?: 'COMPARED' | 'CANNOT_COMPARE';
  price_basis?: 'PER_UNIT' | 'PER_STRIP' | 'PER_PACK' | 'LINE_TOTAL' | 'UNKNOWN';
  price_basis_label?: string;
  basis_source?: string;
  basis_evidence?: string | null;
  billed_unit_price?: number | null;
  unit_label?: string;
  comparison_note?: string | null;
  generic_substitute_available: boolean;
  generic_substitute_store_info: string;
  /** Provenance of the ceiling price — the reference list is a curated subset. */
  data_source: string;
  reference_entry_count: number;
}

/** One row of GET /dawacheck/cases/{id}/benchmark — the server's trust decision per medicine. */
export interface CaseMedicineBenchmark {
  entity_id: string;
  brand_name: string;
  benchmark: DawaCheckBenchmarkResponse | null;
  note: string | null;
  name_provenance: Provenance;
  transcription_task_id: string | null;
  transcription_status: string | null;
  trust: { state?: string; label?: string; benchmarkable?: boolean; reasons?: string[] };
  explanation?: Explanation | null;
}

export interface TranslateInstructionsRequest {
  instructions: string;
  language: 'en' | 'hi' | 'mr';
}

export interface TranslatedInstruction {
  token: string;
  recognized: boolean;
  meaning_en: string;
  translated: string;
}

export interface PrescriptionTranslationResponse {
  original_text: string;
  language: string;
  instructions: TranslatedInstruction[];
  unrecognized_tokens: string[];
}
