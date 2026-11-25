import type { Metadata } from "next";
import "../components/auth/auth.css";
import { AuthSplit } from "../components/auth/AuthSplit";
import { VerifyEmailForm } from "../components/auth/VerifyEmailForm";
import { serverT } from "../i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { tr } = await serverT();
  return { title: tr("Confirm your email address — ArogyaRakshak"), description: tr("Confirm your email address with the code from a verification link.") };
}

/** Email verification with the one-time code from the link fragment (#token=...). */
export default function Page() {
  return (
    <AuthSplit>
      <VerifyEmailForm />
    </AuthSplit>
  );
}
