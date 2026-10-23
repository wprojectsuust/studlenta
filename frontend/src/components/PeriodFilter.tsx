import type { Period } from "@/lib/api";

export const PERIODS: { id: Period; label: string }[] = [
  { id: "all", label: "Все" },
  { id: "today", label: "Сегодня" },
  { id: "week", label: "На этой неделе" },
  { id: "month", label: "В этом месяце" },
];

export function PeriodFilter({ value, onChange }: { value: Period; onChange: (p: Period) => void }) {
  return (
    <div role="group" aria-label="Когда" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {PERIODS.map((p) => {
        const on = p.id === value;
        return (
          <button key={p.id} type="button" aria-pressed={on} onClick={() => onChange(p.id)} className="btn"
            style={{ minHeight: 44, padding: "0 16px", fontSize: 14, background: on ? "var(--color-accent)" : "var(--color-surface)",
              color: on ? "var(--color-on-accent)" : "var(--color-ink)", borderColor: on ? "var(--color-accent)" : "var(--color-line)" }}>
            {p.label}
          </button>
        );
      })}
    </div>
  );
}
