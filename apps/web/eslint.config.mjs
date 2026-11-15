import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Animation libraries are confined to app/motion (lazy loading, reduced-motion handling).
  {
    rules: {
      "no-restricted-imports": [
        "error",
        {
          paths: ["motion", "framer-motion", "lenis", "gsap"].map((name) => ({
            name,
            message: "Import motion patterns from app/motion instead; animation libraries are confined there.",
          })),
          patterns: ["motion/*", "framer-motion/*", "lenis/*", "gsap/*"],
        },
      ],
    },
  },
  { files: ["app/motion/**"], rules: { "no-restricted-imports": "off" } },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Generated / vendored files are not hand-written.
    "app/generated/**",
    "app/shared/**",
  ]),
]);

export default eslintConfig;
