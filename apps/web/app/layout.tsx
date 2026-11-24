import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./motion/motion.css";
import "./shell/shell.css";
import "./components/ui/ui.css";
import "./components/brand/brand.css";
import "./components/illustrations/illustrations.css";
import { fontVariables } from "./fonts";
import { CommandPaletteLauncher } from "./shell/CommandPaletteLauncher";
import { ShellProvider } from "./shell/ShellProvider";
import { SiteFooter } from "./shell/SiteFooter";
import { SiteHeader } from "./shell/SiteHeader";
import { SkipLink } from "./shell/SkipLink";

export const metadata: Metadata = {
  title: "ArogyaRakshak (आरोग्यरक्षक) — Healthcare Cost & Rights Intelligence",
  description:
    "Patient-facing forensic bill audit, IRDAI insurance dispute appeals, PM-JAY scheme eligibility & NPPA medicine pricing platform.",
  applicationName: "ArogyaRakshak",
  // Static files in public/ (not metadata routes), written by scripts/brand-assets.ts from the emblem
  // geometry. PNG 192/512, a maskable 512 and an apple-touch-icon exist; installability is still not
  // verified in a browser. Deliberately NO service worker: offline caching of pages or documents would
  // contradict zero document retention.
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/icons/favicon.svg", type: "image/svg+xml" },
      { url: "/icons/favicon-32.png", sizes: "32x32", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  // Lets the page extend under notches/home indicators; the shell pads with env(safe-area-inset-*).
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F4F1E8" },
    { media: "(prefers-color-scheme: dark)", color: "#F4F1E8" },
  ],
};

/**
 * Light (Deep Forest / Warm Ivory) is the default for everyone; dark is opt-in only (header toggle or
 * settings), never inferred from the OS preference.
 *
 * The app shell (WS4): skip link, sticky header, one <main> landmark, footer. Pages render only
 * their content. global-error.tsx replaces this layout and brings its own minimal frame.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="light" className={fontVariables} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t="light";try{var s=localStorage.getItem("arogyarakshak_theme");if(s==="light"||s==="dark"){t=s;}}catch(e){}document.documentElement.setAttribute("data-theme",t);try{if(localStorage.getItem("arogyarakshak.motion")==="reduce")document.documentElement.setAttribute("data-motion","reduce");}catch(e){}})();`,
          }}
        />
      </head>
      <body>
        <ShellProvider>
          <SkipLink />
          <SiteHeader />
          <main id="main-content" tabIndex={-1} className="shell-main">
            {children}
          </main>
          <SiteFooter />
          <CommandPaletteLauncher />
        </ShellProvider>
      </body>
    </html>
  );
}
