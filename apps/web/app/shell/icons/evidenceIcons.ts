// Evidence-state icons. Part of the one icon map (shell/icons/*, Wave 3 decision D3: lucide-react).
// Each icon is imported from its own `lucide-react/icons/<name>` file, and each group lives in its
// own module, so a page that needs only module icons does not bundle the action or evidence icons.
// Icons are decorative by default (lucide adds aria-hidden when no aria-label/title is given); pair
// every icon with visible text or an aria-label on its control.
import type { LucideIcon } from "lucide-react";
import BadgeCheck from "lucide-react/icons/badge-check";
import BookOpen from "lucide-react/icons/book-open";
import CircleDashed from "lucide-react/icons/circle-dashed";
import FileQuestion from "lucide-react/icons/file-question-mark";
import Hourglass from "lucide-react/icons/hourglass";
import Scale from "lucide-react/icons/scale";
import Sparkles from "lucide-react/icons/sparkles";
import UserRound from "lucide-react/icons/user-round";

/** One icon per evidence state (EvidenceBadge); the badge always shows its text label too. */
export const EVIDENCE_ICONS = {
  verified: BadgeCheck,
  provisional: Hourglass,
  unevaluated: CircleDashed,
  "insufficient-evidence": FileQuestion,
  "ai-generated": Sparkles,
  "rule-engine": Scale,
  "user-provided": UserRound,
  external: BookOpen,
} as const satisfies Record<string, LucideIcon>;
