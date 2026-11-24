import type { Metadata } from "next";
import { SettingsPage } from "../../components/workspace/SettingsPage";
import { InsuranceShieldIllustration } from "../../components/illustrations/Illustrations";

export const metadata: Metadata = {
  title: "Settings — ArogyaRakshak",
  description: "Language, theme, reading and motion preferences, your account and the open case.",
};

export default function Settings() {
  return <SettingsPage privacyArt={<InsuranceShieldIllustration size={72} />} />;
}
