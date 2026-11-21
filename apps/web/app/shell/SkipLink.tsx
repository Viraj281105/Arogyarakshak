"use client";

import React from "react";
import { useLanguage } from "./ShellProvider";
import { shellCopy } from "./shellCopy";

/** First focusable element on every page; visible only while focused. */
export function SkipLink() {
  const [lang] = useLanguage();
  return (
    <a className="site-skip" href="#main-content">
      {shellCopy[lang].skipToContent}
    </a>
  );
}
