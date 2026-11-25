import type React from "react";
import { ArogyaWordmark } from "../brand/Brand";
import { BotanicalGeometryBackground } from "../illustrations/Backgrounds";
import { serverT } from "../../i18n/server";

/**
 * Editorial split for the account pages (transformation M9): a Deep Forest panel with the brand and
 * the privacy facts, and the form beside it. A Server Component (no client directive): the panel
 * renders as HTML and costs no JS. Each fact matches the code and ADRs (ADR-003 no document
 * retention, ADR-026 scrypt + HttpOnly SameSite=Strict session, CASE_TTL_DAYS default 90).
 * Hindi and Marathi are machine translated and not yet reviewed (docs/localization.md).
 */
export async function AuthSplit({ children }: { children: React.ReactNode }) {
  const { tr } = await serverT();
  return (
    <div className="auth-page">
      <div className="auth-split">
        <aside className="auth-brand-panel" aria-label={tr("Privacy and data handling")}>
          <BotanicalGeometryBackground intensity={0.26} />
          <div className="auth-brand-inner">
            <ArogyaWordmark size={40} tone="dark" />
            <p className="auth-brand-promise">
              {tr("Your original file is read, then discarded. Extracted details and a redacted excerpt stay until you delete the case or it expires (90 days by default).")}
            </p>
            <ul className="auth-pillars">
              <li>
                <strong>{tr("No document vault")}</strong>
                <span>{tr("Bills, prescriptions and insurer letters are not kept after they are read.")}</span>
              </li>
              <li>
                <strong>{tr("Protected sign-in")}</strong>
                <span>{tr("Passwords are stored only as scrypt hashes; the web session is an HttpOnly, SameSite=Strict cookie.")}</span>
              </li>
              <li>
                <strong>{tr("Delete when you want")}</strong>
                <span>{tr("Delete a case, or your whole account and its cases, from Settings.")}</span>
              </li>
            </ul>
          </div>
        </aside>
        {children}
      </div>
    </div>
  );
}
