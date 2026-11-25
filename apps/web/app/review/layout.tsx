import type { Metadata } from "next";
import { serverT } from "../i18n/server";

// The page itself is a client component, so its title lives here (Wave 3 M4: /review had none).
export async function generateMetadata(): Promise<Metadata> {
  const { tr } = await serverT();
  return { title: tr("Clinical reviewer workspace — ArogyaRakshak"), description: tr("Sign in as a clinical reviewer to read assigned cases, decide facts and write statements.") };
}

export default function ReviewLayout({ children }: { children: React.ReactNode }) {
  return children;
}
