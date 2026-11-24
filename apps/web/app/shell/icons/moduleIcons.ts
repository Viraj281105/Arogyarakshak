// Module icons. Part of the one icon map (shell/icons/*, Wave 3 decision D3: lucide-react).
// Each icon is imported from its own `lucide-react/icons/<name>` file, and each group lives in its
// own module, so a page that needs only module icons does not bundle the action or evidence icons.
// Icons are decorative by default (lucide adds aria-hidden when no aria-label/title is given); pair
// every icon with visible text or an aria-label on its control.
import type { LucideIcon } from "lucide-react";
import ClipboardCheck from "lucide-react/icons/clipboard-check";
import FileText from "lucide-react/icons/file-text";
import Landmark from "lucide-react/icons/landmark";
import Pill from "lucide-react/icons/pill";
import ReceiptText from "lucide-react/icons/receipt-text";
import ShieldCheck from "lucide-react/icons/shield-check";
import type { ModuleTab } from "../nav";

/** Kadi is shared infrastructure; its user-facing surface is "Documents", not a sixth module. */
export type IconModule = ModuleTab | "kadi";

export const MODULE_ICONS: Record<IconModule, LucideIcon> = {
  kadi: FileText,
  billnyay: ReceiptText,
  daavisetu: ClipboardCheck,
  bimanyay: ShieldCheck,
  schemesetu: Landmark,
  dawacheck: Pill,
};
