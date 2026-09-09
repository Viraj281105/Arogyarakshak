import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ArogyaRakshak (आरोग्यरक्षक) — Healthcare Cost & Rights Intelligence",
  description:
    "Patient-facing forensic bill audit, IRDAI insurance dispute appeals, PM-JAY scheme eligibility & NPPA medicine pricing platform.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#0a0e17",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
