"use client";

import React, { useState } from "react";
import { DataTable, type Column } from "../../components/ui/DataTable";
import { Tabs, Tooltip } from "../../components/ui/Disclosure";
import { ConfirmationDialog, Dialog, Drawer } from "../../components/ui/Overlays";
import { ToastProvider, useToast } from "../../components/ui/Toast";
import { EvidenceBadge } from "../../components/ui/Badges";

// SYNTHETIC rows for the dev gallery only. Not real bills, not real rates.
interface Row {
  id: string;
  item: string;
  billed: number;
  reference: number | null;
  status: string;
}
const ROWS: Row[] = [
  { id: "a", item: "Synthetic ward bed (per day)", billed: 4200, reference: 3000, status: "Above reference" },
  { id: "b", item: "Synthetic blood test", billed: 350, reference: 400, status: "Within reference" },
  { id: "c", item: "Synthetic dressing kit", billed: 900, reference: null, status: "Not compared" },
  { id: "d", item: "Synthetic consultation", billed: 1000, reference: 1000, status: "Within reference" },
];
const inr = (n: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
const COLUMNS: Column<Row>[] = [
  { key: "item", header: "Line item", sortValue: (r) => r.item },
  { key: "billed", header: "Billed", numeric: true, sortValue: (r) => r.billed, cell: (r) => inr(r.billed) },
  { key: "reference", header: "Reference", numeric: true, sortValue: (r) => r.reference, cell: (r) => (r.reference === null ? "—" : inr(r.reference)) },
  { key: "status", header: "Status", sortValue: (r) => r.status },
];

export function TableDemo() {
  return <DataTable caption="Synthetic bill lines (sortable)" columns={COLUMNS} rows={ROWS} rowKey={(r) => r.id} />;
}

export function TabsDemo() {
  return (
    <Tabs
      label="Synthetic finding views"
      items={[
        { id: "summary", label: "Summary", content: <p>Synthetic summary panel. Arrow keys move between tabs.</p> },
        { id: "evidence", label: "Evidence", content: <EvidenceBadge state="rule-engine" showMeaning /> },
        { id: "letter", label: "Draft letter", content: <EvidenceBadge state="ai-generated" showMeaning /> },
      ]}
    />
  );
}

export function TooltipDemo() {
  return (
    <Tooltip content="Supplementary hint. Press Escape to hide it.">
      <button type="button" className="btn btn-secondary btn-compact">
        Hover or focus me
      </button>
    </Tooltip>
  );
}

function ToastButtons() {
  const toast = useToast();
  return (
    <div className="primitives-row">
      <button type="button" className="btn btn-secondary btn-compact" onClick={() => toast({ message: "Synthetic: package prepared.", tone: "success" })}>
        Success toast
      </button>
      <button type="button" className="btn btn-secondary btn-compact" onClick={() => toast({ message: "Synthetic: still processing.", tone: "info" })}>
        Info toast
      </button>
      <button type="button" className="btn btn-secondary btn-compact" onClick={() => toast({ message: "Synthetic: the reference row is outdated.", tone: "warning" })}>
        Warning toast
      </button>
      <button type="button" className="btn btn-secondary btn-compact" onClick={() => toast({ message: "Synthetic: could not reach the server.", tone: "error" })}>
        Error toast (stays)
      </button>
    </div>
  );
}

export function OverlayDemo() {
  const [dialog, setDialog] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [outcome, setOutcome] = useState("nothing yet");
  return (
    <ToastProvider>
      <div className="primitives-row">
        <button type="button" className="btn btn-secondary btn-compact" onClick={() => setDialog(true)}>
          Open dialog
        </button>
        <button type="button" className="btn btn-secondary btn-compact" onClick={() => setConfirm(true)}>
          Open confirmation
        </button>
        <button type="button" className="btn btn-secondary btn-compact" onClick={() => setDrawer(true)}>
          Open side panel
        </button>
      </div>
      <p className="primitives-note" role="status">
        Confirmation result: {outcome}
      </p>
      <ToastButtons />
      <Dialog open={dialog} onClose={() => setDialog(false)} title="Synthetic dialog" description="Focus is trapped; Escape or the close button returns focus to the opener.">
        <p>Body content goes here.</p>
      </Dialog>
      <ConfirmationDialog
        open={confirm}
        onCancel={() => {
          setConfirm(false);
          setOutcome("cancelled");
        }}
        onConfirm={() => {
          setConfirm(false);
          setOutcome("confirmed (nothing was deleted: demo)");
        }}
        title="Delete this synthetic case?"
        consequence="In the real app this removes the case and every extracted detail from the server. It cannot be undone."
        confirmLabel="Delete case"
        destructive
      />
      <Drawer open={drawer} onClose={() => setDrawer(false)} title="Synthetic finding detail">
        <p>Side panel for evidence, finding or entity details.</p>
        <p style={{ marginTop: "1rem" }}>
          <EvidenceBadge state="external" showMeaning />
        </p>
      </Drawer>
    </ToastProvider>
  );
}
