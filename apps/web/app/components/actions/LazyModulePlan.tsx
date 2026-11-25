"use client";

import dynamic from "next/dynamic";
import { LazyPanel } from "../LazyPanel";

export const LazyModulePlan = dynamic(() => import("./ModulePlans").then((m) => m.ModulePlan), {
  loading: () => <LazyPanel minHeight="12rem" />,
});

export const LazyActionTracker = dynamic(() => import("./ActionTracker").then((m) => m.ActionTracker), {
  loading: () => <LazyPanel minHeight="8rem" />,
});
