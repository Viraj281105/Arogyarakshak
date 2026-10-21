import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const SRC = join(process.cwd(), 'src');

/** All files under a directory (recursively), concatenated — for text-level contracts on
 *  code that is split across several files. */
export function readTree(dir: string): string {
  return readdirSync(dir)
    .sort()
    .map((f) => {
      const p = join(dir, f);
      return statSync(p).isDirectory() ? readTree(p) : readFileSync(p, 'utf-8');
    })
    .join('\n');
}

/** The API types (one file per domain under src/api/types/). */
export const apiTypesSource = (): string => readTree(join(SRC, 'api', 'types'));

/** A screen plus its helper folder, e.g. CameraScanScreen.tsx + screens/camera/. */
export function screenSource(screen: string, helperDir?: string): string {
  const parts = [readFileSync(join(SRC, 'screens', `${screen}.tsx`), 'utf-8')];
  const dir = helperDir ? join(SRC, 'screens', helperDir) : null;
  if (dir && existsSync(dir)) parts.push(readTree(dir));
  return parts.join('\n');
}
