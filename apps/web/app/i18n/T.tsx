"use client";

import React from "react";
import type { Vars } from "./format";
import { useT } from "./useT";

/**
 * A translated string for components that are rendered by both Server and Client Components
 * (badges, states, status pages), where a hook cannot be called. Renders text only.
 */
export function T({ k, vars }: { k: string; vars?: Vars }) {
  const tr = useT();
  return <>{tr(k, vars)}</>;
}
