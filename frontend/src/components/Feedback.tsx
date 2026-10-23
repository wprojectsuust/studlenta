import Link from "next/link";
import type { ReactNode } from "react";

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="card" style={{ padding: "48px 24px", textAlign: "center", borderStyle: "dashed", display: "flex", flexDirection: "column", gap: 6, alignItems: "center" }}>
      <strong style={{ fontSize: 16 }}>{title}</strong>
      {children && <span style={{ color: "var(--color-muted)" }}>{children}</span>}
    </div>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", padding: "12px 16px", borderRadius: 12, background: "var(--color-danger-bg)", color: "var(--color-danger-ink)" }}>
      <span style={{ flex: 1 }}>{message}</span>
      {onRetry && <button type="button" className="btn btn-secondary" onClick={onRetry}>Повторить</button>}
    </div>
  );
}

/** Ненавязчивое сообщение внизу экрана; role="status" — экранная читалка прочтёт без перевода фокуса. */
export function Toast({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  return (
    <div role="status" style={{ position: "fixed", left: "50%", bottom: 88, transform: "translateX(-50%)", zIndex: 50, display: "flex", gap: 12, alignItems: "center",
      maxWidth: "calc(100vw - 32px)", padding: "10px 10px 10px 16px", borderRadius: 12, background: "#111827", color: "#FFFFFF", boxShadow: "0 8px 24px rgb(0 0 0 / 0.2)" }}>
      <span>{children}</span>
      <button type="button" onClick={onClose} aria-label="Закрыть" style={{ minWidth: 44, minHeight: 44, border: 0, borderRadius: 8, background: "transparent", color: "#FFFFFF", fontSize: 20 }}>×</button>
    </div>
  );
}

export function LoginToast({ onClose }: { onClose: () => void }) {
  return (
    <Toast onClose={onClose}>
      Чтобы ставить лайки, <Link href="/login" style={{ color: "#B3C6FF", fontWeight: 600 }}>войдите</Link>
    </Toast>
  );
}

export function CardSkeleton() {
  return <div aria-hidden="true" className="card" style={{ height: 172, background: "var(--color-surface)", opacity: 0.7, animation: "pulse 1.2s ease-in-out infinite" }} />;
}
