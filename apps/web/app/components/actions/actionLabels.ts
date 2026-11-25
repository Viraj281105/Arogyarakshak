// Wording for tracked actions. A state is always the user's own record: nothing here says
// "submitted", "accepted" or "approved".
import { msg } from "../../i18n/format";
import type { ActionStatus, ContactMethod } from "../../shared/api-client/accounts";

export type StatusTone = "info" | "warning" | "success" | "neutral";

export const STATUS_LABEL: Record<ActionStatus, string> = {
  planned: msg("Chosen, not done yet"),
  draft_prepared: msg("Draft prepared"),
  sent: msg("You marked this as sent"),
  awaiting_response: msg("Awaiting a response"),
  response_received: msg("Response received (your record)"),
  further_action_needed: msg("Further action needed"),
  resolved: msg("Resolved, confirmed by you"),
  partially_resolved: msg("Partly resolved"),
  unresolved: msg("Not resolved"),
  closed: msg("Closed without resolution"),
  withdrawn: msg("Withdrawn by you"),
};

export const STATUS_TONE: Record<ActionStatus, StatusTone> = {
  planned: "neutral",
  draft_prepared: "info",
  sent: "info",
  awaiting_response: "warning",
  response_received: "info",
  further_action_needed: "warning",
  resolved: "success",
  partially_resolved: "warning",
  unresolved: "warning",
  closed: "neutral",
  withdrawn: "neutral",
};

/** The choices offered under "What happened?". */
export const EVENT_LABEL: Record<ActionStatus, string> = {
  planned: msg("I will do this after all"),
  draft_prepared: msg("I prepared a draft"),
  sent: msg("I sent or raised it"),
  awaiting_response: msg("I am waiting for a reply"),
  response_received: msg("I received a reply"),
  further_action_needed: msg("More action is needed"),
  resolved: msg("It is resolved"),
  partially_resolved: msg("It is partly resolved"),
  unresolved: msg("It was not resolved"),
  closed: msg("Close it"),
  withdrawn: msg("I withdraw it"),
};

export const NEXT_HINT: Record<ActionStatus, string> = {
  planned: msg("Prepare what you need. Record the day you send or raise it."),
  draft_prepared: msg("Read the draft, correct it and send it yourself. Then record the day."),
  sent: msg("Keep any reference number. Record the reply when it arrives."),
  awaiting_response: msg("If no reply comes, follow up in writing and record that too."),
  response_received: msg("Read the reply. Record whether it settles your question."),
  further_action_needed: msg("Decide the next step: follow up, take it to the next level, or get help."),
  resolved: msg("Keep the documents. Reopen this if something changes."),
  partially_resolved: msg("Note what is still open. You can reopen this."),
  unresolved: msg("You can follow up again or take it to the next level."),
  closed: msg("You can reopen this later."),
  withdrawn: msg("You can plan this again later."),
};

export const CONTACT_LABEL: Record<ContactMethod, string> = {
  in_person: msg("In person"),
  phone: msg("Phone"),
  email: msg("Email"),
  letter: msg("Letter"),
  online_portal: msg("Online portal"),
  other: msg("Other"),
};

export const NEEDS_DATE: ReadonlySet<ActionStatus> = new Set(["sent", "response_received"]);
export const ASKS_AMOUNT_CORRECTED: ReadonlySet<ActionStatus> = new Set(["response_received", "resolved", "partially_resolved"]);
