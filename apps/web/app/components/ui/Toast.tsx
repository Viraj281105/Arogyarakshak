"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import X from "lucide-react/icons/x";
import { useT } from "../../i18n/useT";

export type ToastTone = "success" | "info" | "warning" | "error";

export interface ToastInput {
  message: string;
  tone?: ToastTone;
  /** Milliseconds before it hides; 0 keeps it until dismissed. Errors default to 0. */
  duration?: number;
}

interface Toast extends Required<ToastInput> {
  id: number;
}

const ToastContext = createContext<((t: ToastInput) => void) | null>(null);

/** Shows a toast from any component under <ToastProvider>. */
export function useToast(): (t: ToastInput) => void {
  const show = useContext(ToastContext);
  if (!show) throw new Error("useToast must be used inside <ToastProvider>");
  return show;
}

/**
 * Toast stack with two always-present live regions (polite for info/success, assertive for
 * warnings and errors), so screen readers announce each message. Toasts pause while hovered or
 * focused, never steal focus, and errors stay until dismissed.
 */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const next = useRef(1);
  const dismiss = useCallback((id: number) => setToasts((ts) => ts.filter((t) => t.id !== id)), []);
  const show = useCallback((t: ToastInput) => {
    const tone = t.tone ?? "info";
    const duration = t.duration ?? (tone === "error" ? 0 : 6000);
    setToasts((ts) => [...ts.slice(-3), { id: next.current++, message: t.message, tone, duration }]);
  }, []);
  const polite = toasts.filter((t) => t.tone === "success" || t.tone === "info");
  const assertive = toasts.filter((t) => t.tone === "warning" || t.tone === "error");
  return (
    <ToastContext.Provider value={useMemo(() => show, [show])}>
      {children}
      <div className="ui-toasts">
        <div role="status" aria-live="polite">
          {polite.map((t) => (
            <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
          ))}
        </div>
        <div role="alert" aria-live="assertive">
          {assertive.map((t) => (
            <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
          ))}
        </div>
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  const tr = useT();
  const [paused, setPaused] = useState(false);
  useEffect(() => {
    if (!toast.duration || paused) return;
    const h = setTimeout(() => onDismiss(toast.id), toast.duration);
    return () => clearTimeout(h);
  }, [toast, paused, onDismiss]);
  return (
    <div
      className={`ui-toast ui-toast-${toast.tone}`}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <p>{toast.message}</p>
      <button type="button" className="ui-icon-btn" onClick={() => onDismiss(toast.id)} aria-label={tr("Dismiss notification")}>
        <X size={16} aria-hidden="true" />
      </button>
    </div>
  );
}
