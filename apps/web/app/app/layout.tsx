import "../components/workspace/workspace.css";
import "../components/auth/auth.css";

/** Workspace routes (`/app/**`): styles only; every page brings its own client part. */
export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return children;
}
