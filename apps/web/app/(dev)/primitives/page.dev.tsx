import { notFound } from "next/navigation";
import { ConfidenceIndicator, EvidenceBadge, MetricCard, StatusBadge } from "../../components/ui/Badges";
import { BarChart, DonutChart, StackedBarChart, TimelineChart, WaterfallChart } from "../../components/ui/Charts";
import { CITATION_TO_EVIDENCE, EVIDENCE_STATES } from "../../components/ui/evidence";
import { PageHeader } from "../../components/ui/PageHeader";
import { EmptyState, ErrorState, InsufficientEvidenceState, LoadingState, PartialResultState } from "../../components/ui/States";
import { Checklist, StepWizard } from "../../components/ui/Steps";
import { OverlayDemo, TableDemo, TabsDemo, TooltipDemo } from "./InteractiveDemos";
import "./primitives.css";

const SYNTH = "Synthetic example (dev gallery)";

// Dev-only gallery of the Wave 3 primitives. A `page.dev.tsx` file: production builds do not see it
// (next.config.ts), and it 404s if ever served in production. EVERY figure here is synthetic.
export default function PrimitivesPage() {
  if (process.env.NODE_ENV === "production") notFound();
  return (
    <div className="container primitives">
      <PageHeader
        kicker="Dev gallery"
        title="Component primitives"
        lede="Wave 3 M2 building blocks. Every figure on this page is a synthetic example, not data. Press Ctrl+K (Cmd+K on macOS) for the command palette."
        breadcrumbs={[{ label: "Home", href: "/" }, { label: "Dev" }, { label: "Primitives" }]}
        actions={<span className="ui-badge ui-estimate-badge">Synthetic data</span>}
      />

      <section aria-labelledby="p-evidence">
        <h2 id="p-evidence">EvidenceBadge (eight states)</h2>
        <ul className="primitives-stack">
          {EVIDENCE_STATES.map((s) => (
            <li key={s}>
              <EvidenceBadge state={s} showMeaning />
            </li>
          ))}
        </ul>
        <h3>Wave 2 citation status mapping</h3>
        <ul className="primitives-stack">
          {Object.entries(CITATION_TO_EVIDENCE).map(([c, e]) => (
            <li key={c}>
              <code>{c}</code> → <EvidenceBadge state={e} size="sm" />
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="p-status">
        <h2 id="p-status">StatusBadge, ConfidenceIndicator, MetricCard</h2>
        <div className="primitives-row">
          <StatusBadge tone="success">Package ready</StatusBadge>
          <StatusBadge tone="warning">Needs a document</StatusBadge>
          <StatusBadge tone="danger">Processing failed</StatusBadge>
          <StatusBadge tone="info">Processing</StatusBadge>
          <StatusBadge tone="neutral">Not started</StatusBadge>
        </div>
        <div className="primitives-stack">
          <ConfidenceIndicator value={0.93} source="synthetic OCR score" />
          <ConfidenceIndicator value={0.71} source="synthetic OCR score" />
          <ConfidenceIndicator value={0.42} source="synthetic OCR score" />
        </div>
        <div className="primitives-grid">
          <MetricCard label="Above reference (synthetic)" value="₹1,200" basis="verified" source={SYNTH} period="One bill" />
          <MetricCard label="Possible refund (synthetic)" value="₹800–1,200" basis="estimate" source={SYNTH} period="One bill" note="An estimate: depends on the hospital's package terms." />
        </div>
      </section>

      <section aria-labelledby="p-charts">
        <h2 id="p-charts">Charts (SVG, each with a data table)</h2>
        <div className="primitives-grid">
          <BarChart
            title="Billed per line (synthetic)"
            units="₹"
            period="One admission"
            source={SYNTH}
            basis="verified"
            data={[
              { label: "Ward bed", value: 4200, tone: "over" },
              { label: "Blood test", value: 350, tone: "within" },
              { label: "Dressing kit", value: 900, tone: "unmatched" },
            ]}
          />
          <StackedBarChart
            title="Bill composition (synthetic)"
            units="₹"
            period="One admission"
            source={SYNTH}
            series={[
              { key: "within", label: "Within reference", tone: "within" },
              { key: "over", label: "Above reference", tone: "over" },
              { key: "unmatched", label: "Not compared", tone: "unmatched" },
            ]}
            rows={[
              { label: "Day 1", values: { within: 2400, over: 1200, unmatched: 300 } },
              { label: "Day 2", values: { within: 1800, over: 0, unmatched: 600 } },
            ]}
          />
          <DonutChart
            title="Where the bill went (synthetic)"
            units="₹"
            period="One admission"
            source={SYNTH}
            basis="estimate"
            data={[
              { label: "Room", value: 6000, tone: 1 },
              { label: "Tests", value: 2500, tone: 2 },
              { label: "Medicines", value: 1500, tone: 3 },
            ]}
          />
          <WaterfallChart
            title="Billed to payable (synthetic)"
            units="₹"
            period="One claim"
            source={SYNTH}
            basis="estimate"
            start={10000}
            startLabel="Billed"
            steps={[
              { label: "Deductible", value: -1500 },
              { label: "Non-payable", value: -700 },
              { label: "Taxes", value: 300 },
              { label: "Payable", value: 0, total: true },
            ]}
          />
          <TimelineChart
            title="Claim timeline (synthetic)"
            units="days"
            period="2026"
            source={SYNTH}
            events={[
              { date: "2026-01-05", label: "Admitted" },
              { date: "2026-01-09", label: "Discharged" },
              { date: "2026-01-20", label: "Claim filed", detail: "Synthetic detail line." },
              { date: "2026-02-18", label: "Response due" },
            ]}
          />
        </div>
      </section>

      <section aria-labelledby="p-table">
        <h2 id="p-table">DataTable</h2>
        <TableDemo />
      </section>

      <section aria-labelledby="p-overlays">
        <h2 id="p-overlays">Dialog, ConfirmationDialog, Drawer, Toast, Tooltip</h2>
        <OverlayDemo />
        <div className="primitives-row">
          <TooltipDemo />
        </div>
      </section>

      <section aria-labelledby="p-tabs">
        <h2 id="p-tabs">Tabs, StepWizard, Checklist</h2>
        <TabsDemo />
        <StepWizard
          current={1}
          steps={[
            { id: "docs", label: "Documents" },
            { id: "check", label: "Readiness" },
            { id: "form", label: "Form" },
            { id: "pack", label: "Package ready" },
          ]}
        />
        <Checklist
          title="Readiness (synthetic)"
          items={[
            { id: "1", label: "Discharge summary", status: "done" },
            { id: "2", label: "Itemised bill", status: "todo" },
            { id: "3", label: "Policy number", status: "blocked", note: "Synthetic: not found on any document." },
            { id: "4", label: "Pre-existing condition disclosure", status: "unknown" },
          ]}
        />
      </section>

      <section aria-labelledby="p-states">
        <h2 id="p-states">States</h2>
        <div className="primitives-grid">
          <LoadingState label="Reading your document…" />
          <EmptyState title="No case yet" action={<a className="btn btn-secondary btn-compact" href="/app#intake-dropzone">Check a document</a>}>
            Upload a bill, letter or prescription to start.
          </EmptyState>
          <ErrorState action={<button type="button" className="btn btn-secondary btn-compact">Try again</button>}>
            Synthetic: the server did not answer.
          </ErrorState>
          <PartialResultState missing={["Medicine prices (no prescription in this case)", "Scheme eligibility (income not given)"]}>
            Synthetic: the bill was checked.
          </PartialResultState>
          <InsufficientEvidenceState reason="Synthetic: no reference row matches this line." />
        </div>
      </section>
    </div>
  );
}
