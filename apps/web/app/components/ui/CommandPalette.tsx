"use client";

import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import CornerDownLeft from "lucide-react/icons/corner-down-left";
import Search from "lucide-react/icons/search";
import { useLanguage } from "../../shell/ShellProvider";
import { filterCommands, paletteCommands, type Command } from "../../shell/commands";
import { useT } from "../../i18n/useT";

/**
 * Ctrl/Cmd+K palette: a modal <dialog> with a combobox filtering a listbox of the app's existing
 * routes. Arrow keys move the active option (aria-activedescendant), Enter goes there, Escape
 * closes and focus returns to where it was (native dialog behaviour).
 */
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const tr = useT();
  const [lang] = useLanguage();
  const router = useRouter();
  const id = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const results = useMemo(() => filterCommands(paletteCommands(lang), query), [lang, query]);

  useEffect(() => {
    const d = dialog.current;
    if (!d) return;
    if (open && !d.open) {
      setQuery("");
      setActive(0);
      d.showModal();
    }
    if (!open && d.open) d.close();
  }, [open]);

  useEffect(() => {
    const d = dialog.current;
    if (!d) return;
    const onCancel = (e: Event) => {
      e.preventDefault();
      onClose();
    };
    d.addEventListener("cancel", onCancel);
    return () => d.removeEventListener("cancel", onCancel);
  }, [onClose]);

  const go = (cmd: Command | undefined) => {
    if (!cmd) return;
    onClose();
    const [path, hash] = cmd.href.split("#");
    if (path === window.location.pathname && hash !== undefined) {
      window.location.hash = hash; // same page: a real hashchange, which the workspace listens to
    } else {
      router.push(cmd.href);
    }
  };

  const activeId = results[active] ? `${id}-opt-${results[active].id}` : undefined;
  return (
    <dialog
      ref={dialog}
      className="ui-dialog ui-palette"
      aria-label={tr("Go to a page")}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="ui-dialog-panel">
        <div className="ui-palette-input">
          <Search size={18} aria-hidden="true" />
          <input
            autoFocus
            role="combobox"
            aria-expanded="true"
            aria-controls={`${id}-list`}
            aria-activedescendant={activeId}
            aria-autocomplete="list"
            aria-label={tr("Go to a page")}
            placeholder={tr("Go to a page…")}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActive(0);
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActive((a) => Math.min(results.length - 1, a + 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActive((a) => Math.max(0, a - 1));
              } else if (e.key === "Enter") {
                e.preventDefault();
                go(results[active]);
              }
            }}
          />
          <kbd className="ui-kbd">{tr("Esc")}</kbd>
        </div>
        <ul id={`${id}-list`} role="listbox" aria-label={tr("Pages")} className="ui-palette-list">
          {results.length === 0 && (
            <li role="option" aria-selected="false" aria-disabled="true" className="ui-palette-empty">{tr("No page matches “{query}”. The palette only lists pages that exist.", { query: query })}</li>
          )}
          {results.map((cmd, i) => (
            <li
              key={cmd.id}
              id={`${id}-opt-${cmd.id}`}
              role="option"
              aria-selected={i === active}
              className="ui-palette-option"
              onMouseMove={() => setActive(i)}
              onClick={() => go(cmd)}
            >
              <span>{cmd.label}</span>
              <span className="ui-palette-meta">
                {cmd.group} · {cmd.href}
                {i === active && <CornerDownLeft size={14} aria-hidden="true" />}
              </span>
            </li>
          ))}
        </ul>
        <p className="ui-palette-hint">
          <kbd className="ui-kbd">↑</kbd> <kbd className="ui-kbd">↓</kbd>{" "}{tr("to move,")}{" "}<kbd className="ui-kbd">Enter</kbd>{" "}{tr("to open")}</p>
      </div>
    </dialog>
  );
}
