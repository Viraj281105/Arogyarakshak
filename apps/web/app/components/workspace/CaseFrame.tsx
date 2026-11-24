"use client";

import React, { useRef, useState } from "react";
import dynamic from "next/dynamic";
import { usePathname, useRouter } from "next/navigation";
import FilePlus from "lucide-react/icons/file-plus";
import Trash2 from "lucide-react/icons/trash-2";
import { DOCUMENT_ACCEPT } from "../../lib/documentAccept";
import { LazyPanel } from "../LazyPanel";
import { StatePanel } from "../clinical/StatePanel";
import { ConfirmationDialog } from "../ui/Overlays";
import { StatusBadge } from "../ui/Badges";
import { AUTH_PATHS, CASE_PATH, MODULE_ORDER, REPORTS_PATH, WORKSPACE_PATH, isActiveHref, moduleHref } from "../../shell/nav";
import { useLanguage } from "../../shell/ShellProvider";
import { shellCopy } from "../../shell/shellCopy";
import { TransitionLink } from "../../shell/TransitionLink";
import { useCase } from "./CaseProvider";
import { caseCopy } from "./caseCopy";
import { fillCopy, formatDate, shortCaseId } from "./workspaceFormat";

const AgentStreamVisualizer = dynamic(() => import("../AgentStreamVisualizer").then((m) => m.AgentStreamVisualizer), {
  loading: () => <LazyPanel minHeight="12rem" />,
});

/**
 * Frame of every /app/case page: which case is open, its actions (add a document, delete), the
 * processing progress from the server's stream, and the case navigation (overview, five checks,
 * reports). The module pages also work with no case open (stand-alone forms).
 */
export function CaseFrame({ children }: { children: React.ReactNode }) {
  const [lang] = useLanguage();
  const c = caseCopy[lang];
  const tabs = shellCopy[lang].tabs;
  const pathname = usePathname() ?? CASE_PATH;
  const router = useRouter();
  const cs = useCase();
  const fileInput = useRef<HTMLInputElement>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const links = [
    { href: CASE_PATH, label: c.nav.overview },
    ...MODULE_ORDER.map((id) => ({ href: moduleHref(id), label: tabs[id] })),
    { href: REPORTS_PATH, label: c.nav.reports },
  ];

  const onAddDocument = async (file: File | undefined) => {
    if (!file) return;
    setActionError(null);
    try {
      await cs.addDocument(file);
    } catch (err) {
      setActionError(fillCopy(c.frame.addFailed, { reason: err instanceof Error ? err.message : "" }));
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const onDelete = async () => {
    setConfirmDelete(false);
    setDeleting(true);
    setActionError(null);
    try {
      await cs.removeCase();
      router.push(WORKSPACE_PATH);
    } catch (err) {
      setActionError(fillCopy(c.frame.deleteFailed, { reason: err instanceof Error ? err.message : "" }));
    } finally {
      setDeleting(false);
    }
  };

  const ref = cs.ref;
  const created = cs.detail?.case.created_at;

  return (
    <div className="container ws-case">
      <header className="ws-case-head">
        <div className="ws-case-id">
          <p className="ui-kicker">{c.frame.kicker}</p>
          {!cs.hydrated ? (
            <p className="ws-case-title">{c.common.loading}</p>
          ) : ref ? (
            <>
              <p className="ws-case-title">
                {fillCopy(c.frame.caseTitle, { id: shortCaseId(ref.id) })}
                <StatusBadge tone={ref.owned ? "success" : "info"}>{ref.owned ? c.common.owned : c.common.guest}</StatusBadge>
              </p>
              {created && <p className="ws-case-meta">{fillCopy(c.frame.created, { date: formatDate(created, lang) })}</p>}
            </>
          ) : (
            <p className="ws-case-title">{c.frame.noCase}</p>
          )}
        </div>
        {ref && !cs.problem && (
          <div className="ws-case-actions">
            <input
              ref={fileInput}
              type="file"
              accept={DOCUMENT_ACCEPT}
              hidden
              aria-label={c.frame.addDocument}
              onChange={(e) => onAddDocument(e.target.files?.[0])}
            />
            <button
              type="button"
              className="btn btn-secondary btn-compact"
              disabled={!cs.ready}
              title={cs.ready ? undefined : c.frame.addWhenReady}
              onClick={() => fileInput.current?.click()}
            >
              <FilePlus size={16} aria-hidden="true" />
              {c.frame.addDocument}
            </button>
            <button type="button" className="btn btn-danger-outline btn-compact" disabled={deleting} onClick={() => setConfirmDelete(true)}>
              <Trash2 size={16} aria-hidden="true" />
              {deleting ? c.frame.deleting : c.frame.deleteCase}
            </button>
          </div>
        )}
      </header>

      <ConfirmationDialog
        open={confirmDelete}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={onDelete}
        title={c.frame.deleteTitle}
        consequence={c.frame.deleteConsequence}
        confirmLabel={c.frame.deleteConfirm}
        cancelLabel={c.common.cancel}
        destructive
      />

      {actionError && <StatePanel kind="error">{actionError}</StatePanel>}

      {cs.hydrated && ref && cs.problem && (
        <StatePanel kind="error">
          <p>{c.problem[cs.problem]}</p>
          {cs.problem === "signed-out" ? (
            <p>
              <TransitionLink href={`${AUTH_PATHS.login}?next=${encodeURIComponent(CASE_PATH)}`}>{shellCopy[lang].account.signIn}</TransitionLink>
            </p>
          ) : (
            <p>
              <TransitionLink href={WORKSPACE_PATH}>{c.frame.backToDesk}</TransitionLink>
            </p>
          )}
        </StatePanel>
      )}

      {ref && !cs.problem && cs.streamIssue && (
        <StatePanel kind="warning" onRetry={cs.reconnect} retryLabel={c.frame.refreshStatus}>
          {cs.streamIssue === "timeout" ? c.frame.streamTimeout : c.frame.streamLost}
        </StatePanel>
      )}

      {ref && !cs.problem && cs.processingError && <StatePanel kind="error">{fillCopy(c.frame.processingFailed, { reason: cs.processingError })}</StatePanel>}

      {ref && !cs.problem && cs.step > 0 && cs.step < 4 && <AgentStreamVisualizer currentLang={lang} currentStep={cs.step} liveLog={cs.liveLog} />}

      <nav className="ws-case-nav" aria-label={c.nav.label}>
        <ul>
          {links.map((l) => (
            <li key={l.href}>
              <TransitionLink href={l.href} aria-current={isActiveHref(l.href, pathname) && (l.href !== CASE_PATH || pathname === CASE_PATH) ? "page" : undefined}>
                {l.label}
              </TransitionLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="ws-case-body">{children}</div>
    </div>
  );
}
