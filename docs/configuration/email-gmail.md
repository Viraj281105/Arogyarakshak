# Account email through Gmail

Used for email verification and password reset only (ADR-030). Off by default.

**Status:** implemented and unit-tested against a fake HTTP client. **Never run against Google:**
no credentials exist for this project. Treat the first real send as untested.

## What you need

1. A dedicated Gmail or Google Workspace mailbox used only as the sender.
2. A Google Cloud project with the **Gmail API** enabled.
3. An OAuth consent screen with the single scope
   `https://www.googleapis.com/auth/gmail.send`. While the app is in "Testing", add the sender
   mailbox as a test user. Google expires refresh tokens of testing apps after 7 days, so publish
   the consent screen (or use a Workspace internal app) for anything longer.
4. An OAuth client (Web application). For step 5, add
   `https://developers.google.com/oauthplayground` as an authorised redirect URI.
5. A refresh token: in the OAuth 2.0 Playground, open settings, choose "Use your own OAuth
   credentials", authorise the `gmail.send` scope **as the sender mailbox**, and exchange the code
   for tokens. Remove the Playground redirect URI afterwards.

Do these steps yourself in your own browser. Never paste the values into chat, an issue or a commit.

## Configuration

Set these in the API's environment (a git-ignored `.env`, or your secret store):

| Variable | Value |
|---|---|
| `MAIL_TRANSPORT` | `gmail_api` |
| `GMAIL_SENDER` | the mailbox address |
| `GMAIL_CLIENT_ID` | OAuth client id |
| `GMAIL_CLIENT_SECRET` | OAuth client secret |
| `GMAIL_REFRESH_TOKEN` | refresh token from step 5 |
| `WEB_APP_BASE_URL` | public address of the web app, used in links; `https://` required in production |

The API refuses to start when `MAIL_TRANSPORT=gmail_api` and any value is missing.

## Network

The API connects to `oauth2.googleapis.com` and `gmail.googleapis.com` over HTTPS. The Kubernetes
NetworkPolicy in `infrastructure/kubernetes/` leaves egress open; if you restrict egress, allow both
hosts. The Kubernetes manifests do not yet pass the `GMAIL_*` variables to the API.

## Check it

1. Start the API and open `/api/v1/kadi/auth/config`: `email_delivery` must be `true`.
2. Register with an address you control and open the verification link.
3. Use "Forgot password" and complete the reset.
4. Confirm the log shows `Account email (...) accepted by Gmail.` and contains no address or token.

## Behaviour

- Messages are in English, Hindi and Marathi (the latter two machine translated, unreviewed) and
  contain only the link. Verification links last `ACCOUNT_VERIFICATION_TOKEN_TTL_HOURS` (24), reset
  links `PASSWORD_RESET_TOKEN_TTL_MINUTES` (30). Each works once.
- Delivery is best effort with no retry queue. A failure is logged by error type; the person
  requests a new link.
- No mail is sent to the demo account.

## Rotate or revoke

Revoke the app's access in the sender mailbox's Google account settings, or reset the client secret
in the Cloud console, then set new values and restart the API.
