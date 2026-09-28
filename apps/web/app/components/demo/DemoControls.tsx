"use client";

import React, { useRef, useState } from "react";
import {
  DemoCredentials,
  DemoScenario,
  DemoScenarioResult,
  DemoStatus,
  PERSONA_ROLES,
  loadDemoScenario,
  resetDemo,
} from "../../lib/demo";
import { StatePanel } from "../clinical/StatePanel";

const CopyButton: React.FC<{ value: string; label: string }> = ({ value, label }) => {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="btn btn-secondary btn-compact"
      aria-label={`Copy ${label}`}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          window.prompt(`Copy ${label}:`, value);
        }
      }}
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
};

const Credentials: React.FC<{ creds: DemoCredentials }> = ({ creds }) => (
  <div className="demo-credentials">
    <p style={{ margin: "0 0 0.5rem", fontSize: "0.8rem" }}>
      One-time demo credentials — shown now and kept only in this tab&apos;s memory. Reviewer tokens go into the reviewer
      workspace; reviewer IDs are what the patient pastes to assign someone.
    </p>
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Demo persona</th>
            <th>Role in the demo</th>
            <th>Reviewer ID (for assigning)</th>
            <th>Reviewer token (for the workspace)</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(creds.reviewers).map(([key, p]) => (
            <tr key={key}>
              <td>{p.name}</td>
              <td>{PERSONA_ROLES[key] ?? "Demo persona"}</td>
              <td>
                <code style={{ overflowWrap: "anywhere" }}>{p.reviewer_id}</code> <CopyButton value={p.reviewer_id} label={`${p.name} reviewer ID`} />
              </td>
              <td>
                <CopyButton value={p.reviewer_token} label={`${p.name} token`} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    <p style={{ margin: "0.5rem 0 0", fontSize: "0.8rem" }}>
      Scenario B desk: {creds.institution.name} — playbook <code>{creds.playbook_id}</code>{" "}
      <CopyButton value={creds.playbook_id} label="playbook ID" />{" "}
      institution credential <CopyButton value={creds.institution.institution_token} label="institution credential" />
    </p>
  </div>
);

export const DemoControls: React.FC<{
  status: DemoStatus | null;
  onScenarioLoaded: (result: DemoScenarioResult, scenario: DemoScenario) => void;
  onReset: () => void;
}> = ({ status, onScenarioLoaded, onReset }) => {
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const inFlight = useRef(false);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [creds, setCreds] = useState<DemoCredentials | null>(null);
  const [current, setCurrent] = useState<DemoScenario | null>(null);

  if (!status?.demo_mode) return null;

  // One demo operation at a time, even across fast double clicks (the server serialises
  // too; this keeps the UI from queueing a second request).
  const run = async (label: string, fn: () => Promise<void>) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(label);
    setMessage(null);
    try {
      await fn();
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof Error ? err.message : String(err) });
    } finally {
      inFlight.current = false;
      setBusy(null);
    }
  };

  const handleReset = () => {
    const ok = window.confirm(
      "Reset the demo?\n\nThis permanently deletes every case that holds a synthetic demo document, restores the two demo safety rules and issues new demo credentials. Cases with any other document are kept."
    );
    if (!ok) return;
    void run("reset", async () => {
      const res = await resetDemo(key);
      setCreds(res.credentials);
      setCurrent(null);
      onReset();
      setMessage({
        kind: "success",
        text: `Demo reset: ${res.demo_cases_removed} demo case(s) removed, ${res.demo_rules_restored} demo safety rules restored, ${res.other_cases_kept} other case(s) left untouched. New credentials below.`,
      });
    });
  };

  const handleLoad = (scenario: DemoScenario) =>
    run(scenario.id, async () => {
      const res = await loadDemoScenario(key, scenario.id);
      if (res.credentials) setCreds(res.credentials);
      setCurrent(scenario);
      onScenarioLoaded(res, scenario);
      const failed = res.processing.filter((p) => p.status !== "completed");
      setMessage(
        failed.length
          ? { kind: "error", text: `Scenario ${scenario.id} loaded, but ${failed.map((f) => f.filename).join(", ")} did not finish processing.` }
          : { kind: "success", text: `Scenario ${scenario.id} loaded: ${res.documents.join(" + ")} processed into one new case.` }
      );
    });

  const noKey = !key.trim();

  return (
    <details className="card demo-controls" style={{ marginBottom: "1.5rem" }}>
      <summary>
        <strong>Demo controls</strong> <span style={{ fontSize: "0.8rem", opacity: 0.8 }}>(operator only — demo mode)</span>
      </summary>
      <div style={{ display: "grid", gap: "0.75rem", marginTop: "0.75rem" }}>
        {!status.governance_configured && (
          <StatePanel kind="warning">
            The server has no CLINICAL_GOVERNANCE_ADMIN_KEY configured, so reset and scenario loading are disabled.
          </StatePanel>
        )}
        <label style={{ display: "grid", gap: "0.3rem", fontSize: "0.85rem" }}>
          Demo operator key (the server&apos;s CLINICAL_GOVERNANCE_ADMIN_KEY; kept in memory only)
          <input
            type="password"
            className="input-field"
            autoComplete="off"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="Operator key"
          />
        </label>

        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {status.scenarios.map((s) => (
            <button
              key={s.id}
              type="button"
              className="btn btn-primary btn-compact"
              disabled={!!busy || noKey}
              onClick={() => handleLoad(s)}
              title={s.title}
            >
              {busy === s.id ? `Loading ${s.id}…` : `Load Scenario ${s.id}`}
            </button>
          ))}
          <button type="button" className="btn btn-secondary btn-compact" disabled={!!busy || noKey} onClick={handleReset}>
            {busy === "reset" ? "Resetting…" : "Reset demo"}
          </button>
        </div>
        {busy && busy !== "reset" && (
          <StatePanel kind="loading">
            Running the scenario&apos;s synthetic documents through the real upload pipeline… (a few seconds; nothing is
            shown as done until it is)
          </StatePanel>
        )}
        {message && <StatePanel kind={message.kind === "error" ? "error" : "success"}>{message.text}</StatePanel>}

        {current && (
          <div className="demo-script">
            <strong>
              Scenario {current.id}: {current.title}
            </strong>
            <p style={{ margin: "0.3rem 0" }}>
              <em>Starting state:</em> {current.starting_state}
            </p>
            <ol style={{ margin: "0.3rem 0 0.3rem 1.2rem" }}>
              {current.actions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ol>
            <p style={{ margin: 0 }}>
              <em>Expected:</em> {current.expected}
            </p>
          </div>
        )}
        {creds && <Credentials creds={creds} />}
        {!creds && (
          <p style={{ margin: 0, fontSize: "0.8rem", opacity: 0.85 }}>
            Press <strong>Reset demo</strong> first to get the demo reviewers&apos; one-time credentials.
          </p>
        )}
      </div>
    </details>
  );
};
