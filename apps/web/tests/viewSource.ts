import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const MODULES = join(process.cwd(), 'app', 'components', 'modules');

/**
 * Source of a module view for text-level contract tests: `<Name>View.tsx` plus every file
 * in its `<name>/` sub-folder (the view composes those components), so a contract keeps
 * holding when the view is split into smaller files.
 */
export function viewSource(viewName: string): string {
  const parts = [readFileSync(join(MODULES, `${viewName}.tsx`), 'utf-8')];
  const dir = join(MODULES, viewName.replace(/View$/, '').toLowerCase());
  if (existsSync(dir)) {
    for (const f of readdirSync(dir).sort()) parts.push(readFileSync(join(dir, f), 'utf-8'));
  }
  return parts.join('\n');
}
