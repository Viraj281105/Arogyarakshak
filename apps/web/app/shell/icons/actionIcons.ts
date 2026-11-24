// Common action icons. Part of the one icon map (shell/icons/*, Wave 3 decision D3: lucide-react).
// Each icon is imported from its own `lucide-react/icons/<name>` file, and each group lives in its
// own module, so a page that needs only module icons does not bundle the action or evidence icons.
// Icons are decorative by default (lucide adds aria-hidden when no aria-label/title is given); pair
// every icon with visible text or an aria-label on its control.
import type { LucideIcon } from "lucide-react";
import ArrowRight from "lucide-react/icons/arrow-right";
import CircleAlert from "lucide-react/icons/circle-alert";
import CircleCheck from "lucide-react/icons/circle-check";
import Command from "lucide-react/icons/command";
import Download from "lucide-react/icons/download";
import House from "lucide-react/icons/house";
import Info from "lucide-react/icons/info";
import LayoutDashboard from "lucide-react/icons/layout-dashboard";
import Plus from "lucide-react/icons/plus";
import Search from "lucide-react/icons/search";
import Stethoscope from "lucide-react/icons/stethoscope";
import Trash2 from "lucide-react/icons/trash-2";
import TriangleAlert from "lucide-react/icons/triangle-alert";
import Upload from "lucide-react/icons/upload";
import X from "lucide-react/icons/x";

export const ACTION_ICONS = {
  upload: Upload,
  add: Plus,
  delete: Trash2,
  download: Download,
  next: ArrowRight,
  search: Search,
  close: X,
  command: Command,
  home: House,
  workspace: LayoutDashboard,
  reviewer: Stethoscope,
  info: Info,
  warning: TriangleAlert,
  error: CircleAlert,
  success: CircleCheck,
} as const satisfies Record<string, LucideIcon>;

export type ActionIcon = keyof typeof ACTION_ICONS;
