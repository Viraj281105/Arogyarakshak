// Entry point for scripts/checks/i18n.mjs (run under tsx): exits 1 listing keys missing from `common`.
import { common } from "../src/common";
import { findMissingKeys } from "./parity";

const missing = findMissingKeys(common);
if (missing.length > 0) {
  console.error(missing.map((m) => `  ${m}`).join("\n"));
  process.exit(1);
}
