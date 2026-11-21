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

// Slice of the file for one top-level job (two-space indented key under `jobs:`).
function jobBlock(name) {
  const start = lines.findIndex((l) => l === `  ${name}:`);
  assert.ok(start >= 0, `job ${name} not found`);
  let end = lines.length;
  for (let i = start + 1; i < lines.length; i++) {
    if (/^  [A-Za-z0-9_-]+:\s*$/.test(lines[i])) {
      end = i;
      break;
    }
  }
  return lines.slice(start, end);
}

test("terminology-audit is report-only: continue-on-error, not a ci-gate dependency, artifact always uploaded", () => {
  const job = jobBlock("terminology-audit");
  assert.ok(job.some((l) => /^    continue-on-error: true\s*$/.test(l)), "continue-on-error: true missing");

  const gate = jobBlock("ci-gate").join("\n");
  assert.doesNotMatch(gate, /terminology-audit/, "ci-gate must not mention terminology-audit");

  const upload = job.findIndex((l) => l.includes("actions/upload-artifact"));
  assert.ok(upload > 0, "upload-artifact step missing");
  const stepStart = job.slice(0, upload).map((l, i) => ({ l, i })).filter(({ l }) => /^      - name:/.test(l)).pop().i;
  assert.ok(job.slice(stepStart, upload).some((l) => /^        if: always\(\)\s*$/.test(l)), "artifact step must run `if: always()`");
});

test("terminology-audit shell does not hide a crash behind `| tee`", () => {
  const job = jobBlock("terminology-audit").join("\n");
  assert.match(job, /shell: bash/);
  assert.match(job, /set -o pipefail/);
});
