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
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F7F6F2" },
    { media: "(prefers-color-scheme: dark)", color: "#151B18" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t="light";try{var s=localStorage.getItem("arogyarakshak_theme");if(s==="light"||s==="dark"){t=s;}else if(window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches){t="dark";}}catch(e){}document.documentElement.setAttribute("data-theme",t);})();`,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
