/** The chosen UI language, shared by every screen and remembered on the device. */
import type { Language } from '../translations/strings';
import { readSecure, writeSecure } from './secureValue';

const KEY = 'ui_language';
let language: Language = 'en';
let chosen = false;
const listeners = new Set<() => void>();

const isLanguage = (value: unknown): value is Language => value === 'en' || value === 'hi' || value === 'mr';

export function getLanguage(): Language {
  return language;
}

export function subscribeLanguage(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function setLanguage(next: Language): void {
  chosen = true;
  language = next;
  listeners.forEach((l) => l());
  void writeSecure(KEY, next);
}

/** Restores the saved choice at start-up; a choice made meanwhile wins. */
export async function hydrateLanguage(): Promise<void> {
  const saved = await readSecure(KEY);
  if (!chosen && isLanguage(saved)) {
    language = saved;
    listeners.forEach((l) => l());
  }
}
