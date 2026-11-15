import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const file = join(dirname(fileURLToPath(import.meta.url)), "..", "..", ".github", "workflows", "ci.yml");
const lines = readFileSync(file, "utf8").split(/\r?\n/);

test("no workflow line has a literal backslash-n used as a line break", () => {
  const bad = lines
    .map((l, i) => ({ l, n: i + 1 }))
    .filter(({ l }) => /\\n\s+\[/.test(l) || /&&\s*\\n/.test(l));
  assert.deepEqual(bad, []);
});

test("every line ending in a backslash continuation is followed by a non-empty line", () => {
  lines.forEach((l, i) => {
    if (/\\$/.test(l) && !l.trimEnd().endsWith("\\\\")) {
      assert.ok((lines[i + 1] ?? "").trim() !== "", `line ${i + 1} continues into an empty line`);
    }
  });
});

test("ci-gate condition lists INVARIANTS and FOUNDATION as separate continued lines", () => {
  const i = lines.findIndex((l) => l.includes('if [ "$INVARIANTS" = "success" ]'));
  assert.ok(i >= 0);
  assert.match(lines[i], /&& \\$/);
  assert.match(lines[i + 1], /^\s+\[ "\$FOUNDATION" = "success" \] && \\$/);
});
