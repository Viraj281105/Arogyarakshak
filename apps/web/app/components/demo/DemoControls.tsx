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
      className="btn btn-ghost btn-compact"
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
    <h4>One-time demo credentials</h4>
    <p className="bn-fine">
      Shown now and kept only in this tab&apos;s memory. Reviewer tokens go into the reviewer workspace; reviewer IDs are
      what the patient pastes to assign someone.
    </p>
    <ul className="demo-personas">
      {Object.entries(creds.reviewers).map(([key, p]) => (
        <li key={key} className="demo-persona">
          <div className="demo-persona-who">
            <strong>{p.name}</strong>
            <span>{PERSONA_ROLES[key] ?? "Demo persona"}</span>
          </div>
          <div className="demo-persona-row">
            <span className="demo-persona-label">Reviewer ID</span>
            <code>{p.reviewer_id}</code>
            <CopyButton value={p.reviewer_id} label={`${p.name} reviewer ID`} />
          </div>
          <div className="demo-persona-row">
            <span className="demo-persona-label">Workspace token</span>
            <code className="demo-masked" aria-label="hidden">
              ••••••••
            </code>
            <CopyButton value={p.reviewer_token} label={`${p.name} token`} />
          </div>
        </li>
      ))}
    </ul>
    <div className="demo-persona-row">
      <span className="demo-persona-label">Scenario B desk</span>
      <span>
        {creds.institution.name} — playbook <code>{creds.playbook_id}</code>
      </span>
      <CopyButton value={creds.playbook_id} label="playbook ID" />
      <CopyButton value={creds.institution.institution_token} label="institution credential" />
    </div>
    {creds.diabetes_playbook_id && (
      <div className="demo-persona-row">
        <span className="demo-persona-label">Scenario E desk</span>
        <span>
          same institution — playbook <code>{creds.diabetes_playbook_id}</code>
        </span>
        <CopyButton value={creds.diabetes_playbook_id} label="diabetes playbook ID" />
      </div>
    )}
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
    <details className="demo-controls">
      <summary>
        <span className="demo-banner-tag">Operator</span>
        <strong>Demo controls</strong>
        <span className="bn-fine">load a scenario or reset the demo</span>
      </summary>
      <div className="demo-controls-body">
        {!status.governance_configured && (
          <StatePanel kind="warning">
            The server has no CLINICAL_GOVERNANCE_ADMIN_KEY configured, so reset and scenario loading are disabled.
          </StatePanel>
        )}
        <div className="ds-field">
          <label className="input-label" htmlFor="demo-key">
            Demo operator key
            <span className="ds-optional">kept in memory only</span>
          </label>
          <input
            id="demo-key"
            type="password"
            className="input-field"
            autoComplete="off"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="The server's CLINICAL_GOVERNANCE_ADMIN_KEY"
          />
        </div>

        <ul className="demo-scenarios" aria-label="Demo scenarios">
          {status.scenarios.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                className={`demo-scenario ${current?.id === s.id ? "is-current" : ""}`}
                disabled={!!busy || noKey}
                onClick={() => handleLoad(s)}
              >
                <span className="demo-scenario-id" aria-hidden="true">
                  {busy === s.id ? <span className="spinner" /> : s.id}
                </span>
                <span className="demo-scenario-text">
                  <strong>{busy === s.id ? `Loading ${s.id}…` : `Load Scenario ${s.id}`}</strong>
                  <span>{s.title}</span>
                  <span className="demo-scenario-module">{s.module}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
        {noKey && <span className="ds-hint">Enter the operator key to enable the scenarios and reset.</span>}

        <div>
          <button type="button" className="btn btn-danger-outline btn-compact" disabled={!!busy || noKey} onClick={handleReset}>
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
            <h4>
              Scenario {current.id}: {current.title}
            </h4>
            <p>
              <em>Starting state:</em> {current.starting_state}
            </p>
            <ol>
              {current.actions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ol>
            <p>
              <em>Expected:</em> {current.expected}
            </p>
          </div>
        )}
        {creds && <Credentials creds={creds} />}
        {!creds && (
          <p className="bn-fine">
            Press <strong>Reset demo</strong> first to get the demo reviewers&apos; one-time credentials.
          </p>
        )}
      </div>
    </details>
  );
};
