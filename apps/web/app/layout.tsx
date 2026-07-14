import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ArogyaRakshak",
  description:
    "Patient-facing bill audit, scheme eligibility & medicine pricing platform — English/Hindi/Marathi.",
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
