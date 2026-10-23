import Link from "next/link";
import { BackIcon } from "./icons";

/** Шапка экранов без сайдбара: страница события, форма. */
export function PlainHeader({ href, label, children }: { href: string; label: string; children?: React.ReactNode }) {
  return (
    <header style={{ background: "var(--color-surface)", borderBottom: "1px solid var(--color-line)" }}>
      <div style={{ maxWidth: 1240, margin: "0 auto", padding: "12px 24px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <Link href={href} className="btn btn-ghost" style={{ color: "var(--color-accent-text)", paddingLeft: 6 }}>
          <BackIcon size={20} />
          {label}
        </Link>
        {children}
      </div>
    </header>
  );
}
