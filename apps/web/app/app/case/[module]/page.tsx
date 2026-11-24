import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ModuleWorkspace } from "../../../components/workspace/ModuleWorkspace";
import { MODULE_ORDER, isModuleTab } from "../../../shell/nav";
import { shellCopy } from "../../../shell/shellCopy";

// Only the five checks exist; anything else is a 404.
export const dynamicParams = false;

export function generateStaticParams() {
  return MODULE_ORDER.map((module) => ({ module }));
}

export async function generateMetadata({ params }: { params: Promise<{ module: string }> }): Promise<Metadata> {
  const { module } = await params;
  return { title: isModuleTab(module) ? `${shellCopy.en.tabs[module]} — ArogyaRakshak` : "ArogyaRakshak" };
}

/** One check for the open case (`/app/case/<module>`). */
export default async function ModulePage({ params }: { params: Promise<{ module: string }> }) {
  const { module } = await params;
  if (!isModuleTab(module)) notFound();
  return <ModuleWorkspace module={module} />;
}
