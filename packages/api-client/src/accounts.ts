import type { components } from "./generated/schema";

/**
 * Account routes (ADR-026, docs/api/accounts.md) shared by web and mobile: paths, response
 * types from the OpenAPI contract and the password policy the API enforces, so a client can
 * say what is wrong before it sends the form. The API stays the authority.
 */

export type AccountUser = components["schemas"]["UserResponse"];
export type SessionResponse = components["schemas"]["SessionResponse"];
export type AcceptedResponse = components["schemas"]["AcceptedResponse"];
export type OwnedCaseSummary = components["schemas"]["OwnedCaseSummary"];
export type OwnedCaseList = components["schemas"]["OwnedCaseList"];
export type ClaimResponse = components["schemas"]["ClaimResponse"];
export type DeleteAccountResponse = components["schemas"]["DeleteAccountResponse"];
export type AuthConfig = components["schemas"]["AuthConfigResponse"];
export type CaseAction = components["schemas"]["CaseAction"];
export type CaseActionList = components["schemas"]["CaseActionList"];
export type ActionCreate = components["schemas"]["ActionCreate"];
export type ActionEventCreate = components["schemas"]["ActionEventCreate"];
export type ActionStatus = components["schemas"]["ActionStatus"];
export type ActionModule = components["schemas"]["ActionModule"];
export type ActionKind = components["schemas"]["ActionKind"];
export type ContactMethod = components["schemas"]["ContactMethod"];

const K = "/api/v1/kadi";

/** Action and resolution records of a case (ADR-031): the user's own record, never a submission. */
export const caseActionPaths = {
  list: (caseId: string) => `${K}/cases/${encodeURIComponent(caseId)}/actions`,
  events: (caseId: string, actionId: string) =>
    `${K}/cases/${encodeURIComponent(caseId)}/actions/${encodeURIComponent(actionId)}/events`,
  one: (caseId: string, actionId: string) =>
    `${K}/cases/${encodeURIComponent(caseId)}/actions/${encodeURIComponent(actionId)}`,
} as const;

export const accountPaths = {
  config: `${K}/auth/config`,
  register: `${K}/auth/register`,
  login: `${K}/auth/login`,
  logout: `${K}/auth/logout`,
  me: `${K}/auth/me`,
  password: `${K}/auth/password`,
  verificationRequest: `${K}/auth/verification/request`,
  verificationConfirm: `${K}/auth/verification/confirm`,
  resetRequest: `${K}/auth/password-reset/request`,
  resetConfirm: `${K}/auth/password-reset/confirm`,
  cases: `${K}/cases`,
  claim: (caseId: string) => `${K}/cases/${encodeURIComponent(caseId)}/claim`,
} as const;

/** True for the account routes themselves (a 401 there is an answer, not an expired session). */
export function isAuthPath(path: string): boolean {
  return path.startsWith(`${K}/auth/`);
}

export const PASSWORD_MIN_LENGTH = 12;
export const PASSWORD_MAX_LENGTH = 128;

export type PasswordProblem = "too_short" | "too_long" | "only_spaces" | "same_as_email";

/**
 * The API's policy (app/services/passwords.py): 12 to 128 characters after Unicode NFKC
 * normalisation, not only whitespace, not the email address (both trimmed, case-insensitive). No composition rules. Length is
 * counted in code points, as Python's len() does.
 */
export function passwordProblem(password: string, email?: string): PasswordProblem | null {
  const normalized = password.normalize("NFKC");
  const length = [...normalized].length;
  if (length < PASSWORD_MIN_LENGTH) return "too_short";
  if (length > PASSWORD_MAX_LENGTH) return "too_long";
  if (normalized.trim() === "") return "only_spaces";
  if (email && normalized.trim().toLowerCase() === email.trim().toLowerCase()) return "same_as_email";
  return null;
}
