import { CaseFrame } from "../../components/workspace/CaseFrame";
import { CaseProvider } from "../../components/workspace/CaseProvider";

/**
 * Every /app/case page shares the open case (CaseProvider: held in sessionStorage, never in the
 * URL) and its frame (actions, processing progress, case navigation).
 */
export default function CaseLayout({ children }: { children: React.ReactNode }) {
  return (
    <CaseProvider>
      <CaseFrame>{children}</CaseFrame>
    </CaseProvider>
  );
}
