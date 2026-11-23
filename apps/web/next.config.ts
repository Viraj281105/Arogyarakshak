import type { NextConfig } from "next";

// `page.dev.tsx` files (the /motion-lab and /primitives galleries) are routes only under
// `next dev`; production builds do not see them, so dev-only galleries ship no client JS
// (WS4 bundle budget).
const DEFAULT_EXTENSIONS = ["tsx", "ts", "jsx", "js"];

/**
 * Wave 3 M2 route moves. Permanent (308) so bookmarks and links in older docs keep working; Next
 * passes the query string (e.g. `?tab=safety`) through.
 */
export const ROUTE_REDIRECTS = [
  { source: "/clinical-review", destination: "/review", permanent: true },
  { source: "/clinical-review/:path*", destination: "/review/:path*", permanent: true },
] as const;

const nextConfig: NextConfig = {
  pageExtensions:
    process.env.NODE_ENV === "development" ? ["dev.tsx", ...DEFAULT_EXTENSIONS] : DEFAULT_EXTENSIONS,
  async redirects() {
    return ROUTE_REDIRECTS.map((r) => ({ ...r }));
  },
};

export default nextConfig;
