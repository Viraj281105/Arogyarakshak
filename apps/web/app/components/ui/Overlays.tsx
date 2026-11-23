"use client";

import React, { useEffect, useId, useRef } from "react";
import X from "lucide-react/icons/x";

/**
 * Modal surfaces on the native <dialog> element (showModal): the browser provides the focus trap,
 * inert background, Escape to close and focus return to the opener. Animations are CSS-only on
 * motion tokens and are switched off under prefers-reduced-motion (ui.css).
 */
function useModal(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    const onCancel = (e: Event) => {
      e.preventDefault(); // keep React state the source of truth
      onClose();
    };
    d.addEventListener("cancel", onCancel);
    return () => d.removeEventListener("cancel", onCancel);
  }, [onClose]);
  // A click on the backdrop lands on the <dialog> itself (its content box is the inner panel).
  const onClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    if (e.target === e.currentTarget) onClose();
  };
  return { ref, onClick };
}

export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  closeLabel = "Close",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: React.ReactNode;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  closeLabel?: string;
}) {
  const id = useId();
  const { ref, onClick } = useModal(open, onClose);
  return (
    <dialog ref={ref} className="ui-dialog" aria-labelledby={`${id}-t`} aria-describedby={description ? `${id}-d` : undefined} onClick={onClick}>
      <div className="ui-dialog-panel">
        <header className="ui-dialog-head">
          <h2 id={`${id}-t`}>{title}</h2>
          <button type="button" className="ui-icon-btn" onClick={onClose} aria-label={closeLabel}>
            <X size={18} aria-hidden="true" />
          </button>
        </header>
        {description && (
          <div id={`${id}-d`} className="ui-dialog-desc">
            {description}
          </div>
        )}
        {children}
        {footer && <footer className="ui-dialog-foot">{footer}</footer>}
      </div>
    </dialog>
  );
}

/**
 * Confirmation for consequential actions. The consequence is stated in words; the confirm button
 * names the action (never just "OK"); Cancel is first in the tab order and receives focus.
 */
export function ConfirmationDialog({
  open,
  onCancel,
  onConfirm,
  title,
  consequence,
  confirmLabel,
  cancelLabel = "Cancel",
  destructive = false,
}: {
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  title: string;
  consequence: React.ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  destructive?: boolean;
}) {
  return (
    <Dialog
      open={open}
      onClose={onCancel}
      title={title}
      description={consequence}
      footer={
        <>
          <button type="button" className="btn btn-secondary btn-compact" onClick={onCancel} autoFocus>
            {cancelLabel}
          </button>
          <button type="button" className={`btn btn-compact ${destructive ? "btn-danger-outline" : "btn-primary"}`} onClick={onConfirm}>
            {confirmLabel}
          </button>
        </>
      }
    />
  );
}

/** Side panel (evidence, finding or entity details). Modal on all widths; full width on phones. */
export function Drawer({
  open,
  onClose,
  title,
  children,
  side = "end",
  closeLabel = "Close panel",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  side?: "start" | "end";
  closeLabel?: string;
}) {
  const id = useId();
  const { ref, onClick } = useModal(open, onClose);
  return (
    <dialog ref={ref} className={`ui-drawer ui-drawer-${side}`} aria-labelledby={`${id}-t`} onClick={onClick}>
      <div className="ui-drawer-panel">
        <header className="ui-dialog-head">
          <h2 id={`${id}-t`}>{title}</h2>
          <button type="button" className="ui-icon-btn" onClick={onClose} aria-label={closeLabel}>
            <X size={18} aria-hidden="true" />
          </button>
        </header>
        <div className="ui-drawer-body">{children}</div>
      </div>
    </dialog>
  );
}
