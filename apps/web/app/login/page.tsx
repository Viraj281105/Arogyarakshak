import type { Metadata } from "next";
import "../components/auth/auth.css";
import { AuthSplit } from "../components/auth/AuthSplit";
import { LoginForm } from "../components/auth/LoginForm";
import { serverT } from "../i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { tr } = await serverT();
  return { title: tr("Sign in — ArogyaRakshak"), description: tr("Sign in to keep your ArogyaRakshak cases with your account.") };
}

/** Sign-in page (ADR-026). Server shell; the form is a client component. */
export default function Page() {
  return (
    <AuthSplit>
      <LoginForm />
    </AuthSplit>
  );
}
