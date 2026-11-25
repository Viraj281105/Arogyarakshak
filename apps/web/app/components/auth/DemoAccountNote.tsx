"use client";

import { useAccount } from "../../hooks/useAccount";
import { useT } from "../../i18n/useT";

/** Says plainly when the signed-in account is the synthetic demo account (docs/DEMO_GUIDE.md). */
export function DemoAccountNote({ className }: { className: string }) {
  const tr = useT();
  const { user } = useAccount();
  if (!user?.is_demo) return null;
  return (
    <p className={className} role="note">
      {tr("DEMO account: {name}, an invented person. Every document and record in it is synthetic.", { name: user.display_name ?? user.email })}
    </p>
  );
}
