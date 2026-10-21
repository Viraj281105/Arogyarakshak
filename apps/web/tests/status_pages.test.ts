import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const read = (...p: string[]) => readFileSync(join(process.cwd(), 'app', ...p), 'utf-8');

describe('Not-found and error pages', () => {
  it('error boundaries use the Next 16 `retry` prop and never print the error message', () => {
    for (const f of ['error.tsx', 'global-error.tsx']) {
      const src = read(f);
      assert.ok(/retry: \(\) => void/.test(src) && /onClick=\{\(\) => retry\(\)\}/.test(src), `${f} must offer retry`);
      assert.ok(!/error\.message|\{String\(error\)\}/.test(src), `${f} must not render the error message`);
    }
  });

  it('global-error brings its own document, styles and theme', () => {
    const src = read('global-error.tsx');
    assert.ok(/<html/.test(src) && /<body>/.test(src));
    assert.ok(/import "\.\/globals\.css"/.test(src));
    assert.ok(/arogyarakshak_theme/.test(src));
  });

  it('the error component is not named Error (it would shadow the global in instanceof)', () => {
    assert.ok(!/export default function Error\b/.test(read('error.tsx')));
  });
});
