// Pure FAQ filter (help search) model (Wave 3 M3): client-side filtering over the static FAQ. No network, no
// index. Unit-tested in tests/public_site.test.ts.
import type { FaqItem } from "./copy/types";

export type FaqTopic = FaqItem["topic"];

/** Lower-case, strip diacritics and punctuation so "pre-auth", "Pre auth" and "preauth" meet. */
export function normalise(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

/**
 * Items whose question, answer or keywords contain every word of the query (any order), within
 * the chosen topic. An empty query keeps every item of the topic; topic null means all topics.
 */
export function filterFaq<T extends Pick<FaqItem, "question" | "answer" | "keywords" | "topic">>(
  items: readonly T[],
  query: string,
  topic: FaqTopic | null,
): T[] {
  const words = normalise(query).split(" ").filter(Boolean);
  return items.filter((item) => {
    if (topic && item.topic !== topic) return false;
    if (words.length === 0) return true;
    const hay = normalise(`${item.question} ${item.answer.join(" ")} ${item.keywords}`);
    const compact = hay.replace(/ /g, "");
    return words.every((w) => hay.includes(w) || compact.includes(w));
  });
}
