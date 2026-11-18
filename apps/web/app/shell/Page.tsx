import React from "react";

/**
 * Layout primitives for page content inside the shell. No hooks, so they render from Server and
 * Client Components alike. Pages are redesigned one by one later; new page code should use these
 * instead of the older `.container` class so width, gutters and vertical rhythm stay consistent.
 */
export function PageContainer({ children, className = "" }: { children?: React.ReactNode; className?: string }) {
  return <div className={`shell-container${className ? ` ${className}` : ""}`}>{children}</div>;
}

/** A titled page section: pass the id of its heading as `labelledBy`. */
export function PageSection({
  children,
  labelledBy,
  id,
  className = "",
}: {
  children?: React.ReactNode;
  labelledBy: string;
  id?: string;
  className?: string;
}) {
  return (
    <section id={id} className={`shell-section${className ? ` ${className}` : ""}`} aria-labelledby={labelledBy}>
      {children}
    </section>
  );
}
