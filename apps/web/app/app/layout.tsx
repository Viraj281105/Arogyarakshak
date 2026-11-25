import "../components/workspace/workspace.css";
import "../components/auth/auth.css";
import { RequireAccount } from "../components/auth/RequireAccount";

/** Workspace routes (`/app/**`): for signed-in accounts only (ADR-029). The API enforces it. */
export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return <RequireAccount>{children}</RequireAccount>;
}
