"use client";

import React from "react";
import dynamic from "next/dynamic";
import { LazyPanel } from "../LazyPanel";
import { SimpleLanguageToggle } from "../SimpleLanguageToggle";
import { LazyActionTracker } from "../actions/LazyModulePlan";
import { LoadingState } from "../ui/States";
import type { ModuleTab } from "../../shell/nav";
import { useLanguage } from "../../shell/ShellProvider";
import { shellCopy } from "../../shell/shellCopy";
import { useCase } from "./CaseProvider";
import { caseCopy } from "./caseCopy";

const moduleLoading = () => <LazyPanel minHeight="28rem" />;
const BillNyayView = dynamic(() => import("../modules/BillNyayView").then((m) => m.BillNyayView), { loading: moduleLoading });
const BimaNyayView = dynamic(() => import("../modules/BimaNyayView").then((m) => m.BimaNyayView), { loading: moduleLoading });
const DaaviSetuView = dynamic(() => import("../modules/DaaviSetuView").then((m) => m.DaaviSetuView), { loading: moduleLoading });
const SchemeSetuView = dynamic(() => import("../modules/SchemeSetuView").then((m) => m.SchemeSetuView), { loading: moduleLoading });
const DawaCheckView = dynamic(() => import("../modules/DawaCheckView").then((m) => m.DawaCheckView), { loading: moduleLoading });

/**
 * One check on its own page (`/app/case/<module>`). With an open case the view receives it only
 * once extraction has finished, so nothing is computed from a half-built case; without one the
 * views offer their stand-alone forms. Each view is its own chunk.
 */
export function ModuleWorkspace({ module }: { module: ModuleTab }) {
  const [lang] = useLanguage();
  const c = caseCopy[lang];
  const cs = useCase();
  const caseId = cs.ready && cs.ref ? cs.ref.id : "";
  const caseToken = cs.ref?.token ?? "";
  const props = { currentLang: lang, caseId, caseToken };

  return (
    <div className="ws-module">
      <div className="ws-module-head">
        <h1 className="ws-page-title">{shellCopy[lang].tabs[module]}</h1>
        <SimpleLanguageToggle lang={lang} />
      </div>
      {cs.hydrated && !cs.ref && <p className="ws-muted">{c.module.standalone}</p>}
      {cs.ref && !cs.ready && !cs.problem && <LoadingState label={c.module.processing} minHeight="5rem" />}
      <div id={`panel-${module}`}>
        {module === "billnyay" && <BillNyayView {...props} />}
        {module === "bimanyay" && <BimaNyayView {...props} />}
        {module === "daavisetu" && <DaaviSetuView {...props} />}
        {module === "schemesetu" && <SchemeSetuView {...props} />}
        {module === "dawacheck" && <DawaCheckView {...props} />}
      </div>
      {caseId && <LazyActionTracker caseId={caseId} module={module} />}
    </div>
  );
}
