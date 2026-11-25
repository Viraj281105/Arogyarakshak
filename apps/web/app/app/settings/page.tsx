import type { Metadata } from "next";
import { SettingsPage } from "../../components/workspace/SettingsPage";
import { InsuranceShieldIllustration } from "../../components/illustrations/Illustrations";
import { serverT } from "../../i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { tr } = await serverT();
  return { title: tr("Settings — ArogyaRakshak"), description: tr("Language, theme, reading and motion preferences, your account and the open case.") };
}

export default function Settings() {
  return <SettingsPage privacyArt={<InsuranceShieldIllustration size={72} />} />;
}
