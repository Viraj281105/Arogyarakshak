# ADR-030: Account email through the Gmail API

## Status
**Accepted (maintainer directive 2026-11-25: "Gmail preferred, OAuth/API").** Closes the open
"email delivery channel" item of ADR-026 §11. **Not yet exercised against Google:** no credentials
exist for this project; tests use a fake HTTP opener.

## Context
Sign-in is now required (ADR-029), so verification and password reset need a delivery channel.
ADR-026 shipped none. Sending mail is a new network boundary (AGENTS.md "Network Boundaries").

## Decision
1. `MAIL_TRANSPORT=disabled` (default) or `gmail_api`. Disabled means no outbound request at all.
2. `services/mail_gmail.GmailApiTransport` uses the Python standard library to exchange an OAuth 2.0
   refresh token at `oauth2.googleapis.com` and send through `gmail.googleapis.com`. No new
   dependency. SMTP with an app password was rejected: it is a long-lived password with wider reach
   than a `gmail.send` token.
3. A message carries no healthcare information. It holds a single-use, expiring token in the URL
   fragment, which browsers do not send to servers.
4. No address, token, credential or provider response body is logged.
5. Delivery runs on one background thread, so a reset request takes the same time whether or not
   the account exists. Responses are identical for known and unknown addresses.
6. Start-up refuses an incomplete Gmail configuration; production requires an `https`
   `WEB_APP_BASE_URL`.
7. `GET /api/v1/kadi/auth/config` tells the client only whether email delivery exists.

## Consequences
- A new outbound boundary: Google receives the recipient address, the sender and the message.
- Delivery is best effort. A failed send is logged by exception type; there is no retry queue. The
  person asks for a new link.
- A process restart drops mail still queued.
- Gmail sending limits apply; this is not a bulk mail service.

## Operator setup
docs/configuration/email-gmail.md.
