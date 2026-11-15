import { runBuild } from "../../packages/api-client/build.mjs";

export default async function generate() {
  await runBuild();
}
