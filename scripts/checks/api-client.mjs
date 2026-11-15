import { runBuild } from "../../packages/api-client/build.mjs";

/** Fails when schema.d.ts is stale against docs/api/openapi.json, or a vendored copy is stale or orphaned. */
export default async function check() {
  await runBuild({ check: true });
}
