/**
 * Demo kit client (demo mode only).
 *
 * The server decides whether it is in demo mode (`GET /kadi/clinical-demo/status`); the
 * client never assumes it. Mutating calls carry the operator's governance key, which is
 * held in component memory only — never written to storage.
 */

import { API_BASE, normalizeErrorDetail } from "../hooks/useApi";

export interface SimulatedItem {
  item: string;
  status: "SIMULATED" | "REAL" | "REAL (rule-based)" | string;
  detail: string;
}

export interface DemoScenario {
  id: "A" | "B" | "C" | "D";
  title: string;
  module: string;
  documents: string[];
  starting_state: string;
  actions: string[];
  expected: string;
}

export interface DemoStatus {
  demo_mode: boolean;
  banner: string | null;
  simulated: SimulatedItem[];
  scenarios: DemoScenario[];
  governance_configured: boolean;
}

export interface DemoPersona {
  reviewer_id: string;
  name: string;
  reviewer_token: string;
}

export interface DemoCredentials {
  warning: string;
  reviewers: Record<string, DemoPersona>;
  institution: { institution_id: string; name: string; institution_token: string };
  playbook_id: string;
}

export interface DemoResetResult {
  status: "reset";
  demo_cases_removed: number;
  other_cases_kept: number;
  demo_rules_restored: number;
  credentials: DemoCredentials;
}

export interface DemoScenarioResult {
  scenario: DemoScenario["id"];
  title: string;
  case_id: string;
  access_token: string;
  documents: string[];
  processing: { filename: string; status: string | null; log: string | null }[];
  credentials: DemoCredentials | null;
}

export const RESET_CONFIRMATION = "RESET DEMO";

async function demoFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1/kadi/clinical-demo${path}`, init);
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail !== undefined) message = normalizeErrorDetail(body.detail);
    } catch {
      // keep the status message
    }
    throw new Error(message);
  }
  return (await res.json()) as T;
}

export function fetchDemoStatus(): Promise<DemoStatus> {
  return demoFetch<DemoStatus>("/status");
}

const keyHeaders = (key: string) => ({ "Content-Type": "application/json", "X-Governance-Admin-Key": key });

export function resetDemo(key: string): Promise<DemoResetResult> {
  return demoFetch<DemoResetResult>("/reset", {
    method: "POST",
    headers: keyHeaders(key),
    body: JSON.stringify({ confirm: RESET_CONFIRMATION }),
  });
}

export function loadDemoScenario(key: string, id: DemoScenario["id"]): Promise<DemoScenarioResult> {
  return demoFetch<DemoScenarioResult>(`/scenarios/${id}`, { method: "POST", headers: keyHeaders(key) });
}

/** Human labels for the demo personas, in the order a demo uses them. */
export const PERSONA_ROLES: Record<string, string> = {
  clinician_a: "Doctor — Scenario A statement (demo board member)",
  clinician_b: "Doctor — Scenario B confirmation, second board member",
  pharmacist: "Reader 1 — Scenario C",
  transcriptionist: "Reader 2 — Scenario C",
};

/** The status of a simulated-components row, for a badge. */
export function simulatedTone(status: string): "demo" | "success" | "machine" {
  if (status === "SIMULATED") return "demo";
  if (status === "REAL") return "success";
  return "machine";
}
