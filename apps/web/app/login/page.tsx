import type { Metadata } from "next";
import "../components/auth/auth.css";
import { AuthSplit } from "../components/auth/AuthSplit";
import { LoginForm } from "../components/auth/LoginForm";

export const metadata: Metadata = {
  title: "Sign in — ArogyaRakshak",
  description: "Sign in to keep your ArogyaRakshak cases with your account.",
};

/** Sign-in page (ADR-026). Server shell; the form is a client component. */
export default function Page() {
  return (
    <AuthSplit>
      <LoginForm />
    </AuthSplit>
  );
}
