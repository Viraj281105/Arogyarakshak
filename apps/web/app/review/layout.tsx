import type { Metadata } from "next";

// The page itself is a client component, so its title lives here (Wave 3 M4: /review had none).
export const metadata: Metadata = {
  title: "Clinical reviewer workspace — ArogyaRakshak",
  description: "Sign in as a clinical reviewer to read assigned cases, decide facts and write statements.",
};

export default function ReviewLayout({ children }: { children: React.ReactNode }) {
  return children;
}
