import type { EventStatus } from "@/lib/api";

const STATUS: Record<EventStatus, { label: string; bg: string; fg: string }> = {
  draft: { label: "Черновик", bg: "var(--color-chip)", fg: "var(--color-ink)" },
  pending: { label: "На проверке", bg: "var(--color-info-bg)", fg: "var(--color-info-ink)" },
  changes_requested: { label: "Нужны правки", bg: "var(--color-warning-bg)", fg: "var(--color-warning-ink)" },
  published: { label: "Опубликовано", bg: "var(--color-success-bg)", fg: "var(--color-success-ink)" },
  rejected: { label: "Отклонено", bg: "var(--color-danger-bg)", fg: "var(--color-danger-ink)" },
  archived: { label: "В архиве", bg: "var(--color-chip)", fg: "var(--color-muted)" },
};

export const statusLabel = (s: EventStatus) => STATUS[s].label;

/** Статус всегда подписан текстом; цвет — дополнительный сигнал. */
export function StatusBadge({ status }: { status: EventStatus }) {
  const s = STATUS[status];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "2px 10px", borderRadius: 999, background: s.bg, color: s.fg, fontSize: 13, fontWeight: 600 }}>
      <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: 999, background: "currentColor" }} />
      {s.label}
    </span>
  );
}
