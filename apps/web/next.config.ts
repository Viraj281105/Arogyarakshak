import type { NextConfig } from "next";

// `page.dev.tsx` files (the /motion-lab gallery) are routes only under `next dev`; production
// builds do not see them, so dev-only galleries ship no client JS (WS4 bundle budget).
const DEFAULT_EXTENSIONS = ["tsx", "ts", "jsx", "js"];

const nextConfig: NextConfig = {
  pageExtensions:
    process.env.NODE_ENV === "development" ? ["dev.tsx", ...DEFAULT_EXTENSIONS] : DEFAULT_EXTENSIONS,
};

export default nextConfig;
