"use client";

import React, { useId, useMemo, useState } from "react";
import type { FaqItem } from "./copy/types";
import { filterFaq, type FaqTopic } from "./faqFilter";

export interface HelpSearchLabels {
  label: string;
  filterLabel: string;
  placeholder: string;
  all: string;
  empty: string;
  /** "{n} of {total} questions" */
  count: string;
  topics: Record<FaqTopic, string>;
}

/**
 * Searchable FAQ for /help. The items and labels come from the server page as props (they are in
 * the RSC payload, not in this bundle). Without JavaScript the server-rendered list is still
 * complete; the search box only narrows it.
 */
export function HelpSearch({ items, labels }: { items: readonly FaqItem[]; labels: HelpSearchLabels }) {
  const [query, setQuery] = useState("");
  const [topic, setTopic] = useState<FaqTopic | null>(null);
  const inputId = useId();
  const statusId = useId();
  const shown = useMemo(() => filterFaq(items, query, topic), [items, query, topic]);
  const topics = Object.keys(labels.topics) as FaqTopic[];

  return (
    <div>
      <div className="pub-search" role="search">
        <label htmlFor={inputId}>{labels.label}</label>
        <input
          id={inputId}
          type="search"
          value={query}
          placeholder={labels.placeholder}
          autoComplete="off"
          aria-describedby={statusId}
          onChange={(e) => setQuery(e.target.value)}
        />
        <ul className="pub-chips" aria-label={labels.filterLabel}>
          <li>
            <button type="button" className="pub-chip" aria-pressed={topic === null} onClick={() => setTopic(null)}>
              {labels.all}
            </button>
          </li>
          {topics.map((t) => (
            <li key={t}>
              <button type="button" className="pub-chip" aria-pressed={topic === t} onClick={() => setTopic(t)}>
                {labels.topics[t]}
              </button>
            </li>
          ))}
        </ul>
        <p id={statusId} className="pub-search-count" role="status" aria-live="polite">
          {shown.length === 0
            ? labels.empty
            : labels.count.replace("{n}", String(shown.length)).replace("{total}", String(items.length))}
        </p>
      </div>
      <ul className="pub-faq">
        {shown.map((f) => (
          <li key={f.id} id={`faq-${f.id}`}>
            <details>
              <summary>{f.question}</summary>
              <div className="pub-faq-answer">
                {f.answer.map((p, i) => (
                  <p key={i}>{p}</p>
                ))}
              </div>
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
}
