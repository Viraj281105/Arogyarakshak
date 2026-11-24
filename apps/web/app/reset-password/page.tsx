import type { Metadata } from "next";
import "../components/auth/auth.css";
import { AuthSplit } from "../components/auth/AuthSplit";
import { ResetPasswordForm } from "../components/auth/ResetPasswordForm";

export const metadata: Metadata = {
  title: "Set a new password — ArogyaRakshak",
  description: "Set a new password with the code from a reset link.",
};

/** Password reset with the one-time code from the link fragment (#token=...). */
export default function Page() {
  return (
    <AuthSplit>
      <ResetPasswordForm />
    </AuthSplit>
  );
}
