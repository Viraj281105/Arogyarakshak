import type { Metadata } from "next";
import "../components/auth/auth.css";
import { AuthSplit } from "../components/auth/AuthSplit";
import { ForgotPasswordForm } from "../components/auth/ForgotPasswordForm";
import { serverT } from "../i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { tr } = await serverT();
  return { title: tr("Forgot your password — ArogyaRakshak"), description: tr("Ask for a password-reset link.") };
}

/** Password-reset request (ADR-026). States that this server cannot send email yet. */
export default function Page() {
  return (
    <AuthSplit>
      <ForgotPasswordForm />
    </AuthSplit>
  );
}
