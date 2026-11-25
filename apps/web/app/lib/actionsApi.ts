// Action and resolution records of the open case (ADR-031). The session cookie authorizes each
// call; nothing is sent to any institution.
import { caseActionPaths, type ActionCreate, type ActionEventCreate, type CaseAction, type CaseActionList } from "../shared/api-client/accounts";
import { apiErrorMessage, apiFetch } from "./apiFetch";

export const ACTIONS_CHANGED = "arogya:actions-changed";

async function send<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, { headers: { Accept: "application/json", ...(init.body ? { "Content-Type": "application/json" } : {}) }, ...init });
  if (!res.ok) throw new Error(await apiErrorMessage(res));
  return (res.status === 204 ? undefined : await res.json()) as T;
}

function changed<T>(value: T): T {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(ACTIONS_CHANGED));
  return value;
}

export function listActions(caseId: string): Promise<CaseAction[]> {
  return send<CaseActionList>(caseActionPaths.list(caseId)).then((body) => body.actions);
}

export function createAction(caseId: string, body: ActionCreate): Promise<CaseAction> {
  return send<CaseAction>(caseActionPaths.list(caseId), { method: "POST", body: JSON.stringify(body) }).then(changed);
}

export function recordActionEvent(caseId: string, actionId: string, body: ActionEventCreate): Promise<CaseAction> {
  return send<CaseAction>(caseActionPaths.events(caseId, actionId), { method: "POST", body: JSON.stringify(body) }).then(changed);
}

export function deleteAction(caseId: string, actionId: string): Promise<void> {
  return send<void>(caseActionPaths.one(caseId, actionId), { method: "DELETE" }).then(changed);
}
