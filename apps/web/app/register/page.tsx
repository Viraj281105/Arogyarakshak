import type { Metadata } from "next";
import "../components/auth/auth.css";
import { AuthSplit } from "../components/auth/AuthSplit";
import { RegisterForm } from "../components/auth/RegisterForm";
import { serverT } from "../i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { tr } = await serverT();
  return { title: tr("Create an account — ArogyaRakshak"), description: tr("Create an ArogyaRakshak account to keep your cases across visits.") };
}

/** Registration page (ADR-026). The API answers the same for a new and an existing address. */
export default function Page() {
  return (
    <AuthSplit>
      <RegisterForm />
    </AuthSplit>
  );
}
