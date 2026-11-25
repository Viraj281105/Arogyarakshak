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
import { useT } from "../../i18n/useT";

const CopyButton: React.FC<{ value: string; label: string }> = ({ value, label }) => {
  const tr = useT();
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="btn btn-ghost btn-compact"
      aria-label={tr("Copy {label}", { label: label })}
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
      {copied ? tr("Copied") : tr("Copy")}
    </button>
  );
};

const Credentials: React.FC<{ creds: DemoCredentials }> = ({ creds }) => {
  const tr = useT();
  return (
  <div className="demo-credentials">
    <h4>{tr("One-time demo credentials")}</h4>
    <p className="bn-fine">{tr("Shown now and kept only in this tab's memory. Reviewer tokens go into the reviewer workspace; reviewer IDs are what the patient pastes to assign someone.")}</p>
    <ul className="demo-personas">
      {Object.entries(creds.reviewers).map(([key, p]) => (
        <li key={key} className="demo-persona">
          <div className="demo-persona-who">
            <strong>{p.name}</strong>
            <span>{PERSONA_ROLES[key] ?? tr("Demo persona")}</span>
          </div>
          <div className="demo-persona-row">
            <span className="demo-persona-label">{tr("Reviewer ID")}</span>
            <code>{p.reviewer_id}</code>
            <CopyButton value={p.reviewer_id} label={tr("{name} reviewer ID", { name: p.name })} />
          </div>
          <div className="demo-persona-row">
            <span className="demo-persona-label">{tr("Workspace token")}</span>
            <code className="demo-masked" aria-label={tr("hidden")}>
              ••••••••
            </code>
            <CopyButton value={p.reviewer_token} label={tr("{name} token", { name: p.name })} />
          </div>
        </li>
      ))}
    </ul>
    <div className="demo-persona-row">
      <span className="demo-persona-label">{tr("Scenario B desk")}</span>
      <span>
        {creds.institution.name}{" "}{tr("— playbook")}{" "}<code>{creds.playbook_id}</code>
      </span>
      <CopyButton value={creds.playbook_id} label={tr("playbook ID")} />
      <CopyButton value={creds.institution.institution_token} label={tr("institution credential")} />
    </div>
    {creds.diabetes_playbook_id && (
      <div className="demo-persona-row">
        <span className="demo-persona-label">{tr("Scenario E desk")}</span>
        <span>{tr("same institution — playbook")}{" "}<code>{creds.diabetes_playbook_id}</code>
        </span>
        <CopyButton value={creds.diabetes_playbook_id} label={tr("diabetes playbook ID")} />
      </div>
    )}
  </div>
);
};

export const DemoControls: React.FC<{
  status: DemoStatus | null;
  onScenarioLoaded: (result: DemoScenarioResult, scenario: DemoScenario) => void;
  onReset: () => void;
}> = ({ status, onScenarioLoaded, onReset }) => {
  const tr = useT();
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
      tr("Reset the demo?\n\nThis permanently deletes every case that holds a synthetic demo document, restores the two demo safety rules and issues new demo credentials. Cases with any other document are kept.")
    );
    if (!ok) return;
    void run("reset", async () => {
      const res = await resetDemo(key);
      setCreds(res.credentials);
      setCurrent(null);
      onReset();
      setMessage({
        kind: "success",
        text: tr("Demo reset: {demo_cases_removed} demo case(s) removed, {demo_rules_restored} demo safety rules restored, {other_cases_kept} other case(s) left untouched. New credentials below.", { demo_cases_removed: res.demo_cases_removed, demo_rules_restored: res.demo_rules_restored, other_cases_kept: res.other_cases_kept }),
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
          ? { kind: "error", text: tr("Scenario {id} loaded, but {value} did not finish processing.", { id: scenario.id, value: failed.map((f) => f.filename).join(", ") }) }
          : { kind: "success", text: tr("Scenario {id} loaded: {value} processed into one new case.", { id: scenario.id, value: res.documents.join(" + ") }) }
      );
    });

  const noKey = !key.trim();

  return (
    <details className="demo-controls">
      <summary>
        <span className="demo-banner-tag">{tr("Operator")}</span>
        <strong>{tr("Demo controls")}</strong>
        <span className="bn-fine">{tr("load a scenario or reset the demo")}</span>
      </summary>
      <div className="demo-controls-body">
        {!status.governance_configured && (
          <StatePanel kind="warning">{tr("The server has no CLINICAL_GOVERNANCE_ADMIN_KEY configured, so reset and scenario loading are disabled.")}</StatePanel>
        )}
        <div className="ds-field">
          <label className="input-label" htmlFor="demo-key">{tr("Demo operator key")}<span className="ds-optional">{tr("kept in memory only")}</span>
          </label>
          <input
            id="demo-key"
            type="password"
            className="input-field"
            autoComplete="off"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder={tr("The server's CLINICAL_GOVERNANCE_ADMIN_KEY")}
          />
        </div>

        <ul className="demo-scenarios" aria-label={tr("Demo scenarios")}>
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
                  <strong>{busy === s.id ? tr("Loading {id}…", { id: s.id }) : tr("Load Scenario {id}", { id: s.id })}</strong>
                  <span>{s.title}</span>
                  <span className="demo-scenario-module">{s.module}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
        {noKey && <span className="ds-hint">{tr("Enter the operator key to enable the scenarios and reset.")}</span>}

        <div>
          <button type="button" className="btn btn-danger-outline btn-compact" disabled={!!busy || noKey} onClick={handleReset}>
            {busy === "reset" ? tr("Resetting…") : tr("Reset demo")}
          </button>
        </div>
        {busy && busy !== "reset" && (
          <StatePanel kind="loading">{tr("Running the scenario's synthetic documents through the real upload pipeline… (a few seconds; nothing is shown as done until it is)")}</StatePanel>
        )}
        {message && <StatePanel kind={message.kind === "error" ? "error" : "success"}>{message.text}</StatePanel>}

        {current && (
          <div className="demo-script">
            <h4>{tr("Scenario {id}: {title}", { id: current.id, title: current.title })}</h4>
            <p>
              <em>{tr("Starting state:")}</em> {current.starting_state}
            </p>
            <ol>
              {current.actions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ol>
            <p>
              <em>{tr("Expected:")}</em> {current.expected}
            </p>
          </div>
        )}
        {creds && <Credentials creds={creds} />}
        {!creds && (
          <p className="bn-fine">{tr("Press “Reset demo” first to get the demo reviewers' one-time credentials.")}</p>
        )}
      </div>
    </details>
  );
};
