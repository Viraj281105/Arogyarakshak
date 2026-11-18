import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./motion/motion.css";
import "./shell/shell.css";
import { fontVariables } from "./fonts";
import { ShellProvider } from "./shell/ShellProvider";
import { SiteFooter } from "./shell/SiteFooter";
import { SiteHeader } from "./shell/SiteHeader";
import { SkipLink } from "./shell/SkipLink";

export const metadata: Metadata = {
  title: "ArogyaRakshak (आरोग्यरक्षक) — Healthcare Cost & Rights Intelligence",
  description:
    "Patient-facing forensic bill audit, IRDAI insurance dispute appeals, PM-JAY scheme eligibility & NPPA medicine pricing platform.",
  applicationName: "ArogyaRakshak",
  // Static files in public/ (not metadata routes): installable shell, deliberately NO service
  // worker — offline caching of pages or documents would contradict zero document retention.
  manifest: "/manifest.webmanifest",
  icons: { icon: [{ url: "/icons/icon.svg", type: "image/svg+xml" }] },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  // Lets the page extend under notches/home indicators; the shell pads with env(safe-area-inset-*).
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F7F6F2" },
    { media: "(prefers-color-scheme: dark)", color: "#151B18" },
  ],
};

/**
 * The app shell (WS4): skip link, sticky header, one <main> landmark, footer. Pages render only
 * their content. global-error.tsx replaces this layout and brings its own minimal frame.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={fontVariables} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t="light";try{var s=localStorage.getItem("arogyarakshak_theme");if(s==="light"||s==="dark"){t=s;}else if(window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches){t="dark";}}catch(e){}document.documentElement.setAttribute("data-theme",t);})();`,
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
        </ShellProvider>
      </body>
    </html>
  );
}
