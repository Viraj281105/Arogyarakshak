import { runBuild } from "../../packages/design-tokens/build.mjs";

/** Fails when the generated token outputs are stale relative to tokens.json. */
export default async function check() {
  runBuild({ check: true });
}
