"use client";

import React, { useCallback, useEffect, useState } from "react";
import { isPaletteShortcut } from "./commands";

type PaletteComponent = typeof import("../components/ui/CommandPalette").CommandPalette;

/**
 * Global Ctrl/Cmd+K listener mounted once in the root layout. The palette is fetched with a plain
 * dynamic import() on the first shortcut, so every route carries only this listener (no
 * next/dynamic runtime either).
 */
export function CommandPaletteLauncher() {
  const [open, setOpen] = useState(false);
  const [Palette, setPalette] = useState<PaletteComponent | null>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!isPaletteShortcut(e)) return;
      e.preventDefault();
      setOpen((o) => !o);
      import("../components/ui/CommandPalette")
        .then((m) => setPalette(() => m.CommandPalette))
        .catch(() => setOpen(false));
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);
  const close = useCallback(() => setOpen(false), []);
  return Palette ? <Palette open={open} onClose={close} /> : null;
}
