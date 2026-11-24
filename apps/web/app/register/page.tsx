import type { Metadata } from "next";
import "../components/auth/auth.css";
import { RegisterForm } from "../components/auth/RegisterForm";

export const metadata: Metadata = {
  title: "Create an account — ArogyaRakshak",
  description: "Create an ArogyaRakshak account to keep your cases across visits.",
};

/** Registration page (ADR-026). The API answers the same for a new and an existing address. */
export default function Page() {
  return <RegisterForm />;
}
