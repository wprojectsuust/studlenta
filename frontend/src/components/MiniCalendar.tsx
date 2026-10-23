"use client";

import Link from "next/link";
import { dayKey, monthTitle } from "@/lib/format";
import { useCalendar } from "@/lib/queries";

const WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"];

/** Месяц с точками в дни, где есть события. Дни — ссылки в календарь. */
export function MiniCalendar({ now = new Date() }: { now?: Date }) {
  const today = dayKey(now);
  const [year, month] = today.split("-").map(Number) as [number, number];
  const key = `${year}-${String(month).padStart(2, "0")}`;
  const { data } = useCalendar(key);
  const counts = new Map(data?.map((d) => [d.date, d.count]));
  const lead = (new Date(Date.UTC(year, month - 1, 1)).getUTCDay() + 6) % 7;
  const days = new Date(Date.UTC(year, month, 0)).getUTCDate();

  return (
    <section className="card" style={{ padding: 18 }} aria-labelledby="mini-cal">
      <h2 id="mini-cal" style={{ fontSize: 15, marginBottom: 10 }}>{monthTitle(year, month)}</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(0, 1fr))", gap: 2, textAlign: "center", fontSize: 12 }}>
        {WEEKDAYS.map((w) => <span key={w} aria-hidden="true" style={{ color: "var(--color-muted)", paddingBottom: 4 }}>{w}</span>)}
        {Array.from({ length: lead }, (_, i) => <span key={`l${i}`} />)}
        {Array.from({ length: days }, (_, i) => {
          const date = `${key}-${String(i + 1).padStart(2, "0")}`;
          const count = counts.get(date) ?? 0;
          const isToday = date === today;
          return (
            <Link key={date} href={`/calendar?date=${date}`} aria-label={`${i + 1}${isToday ? ", сегодня" : ""}${count ? `, событий: ${count}` : ""}`}
              style={{ minHeight: 34, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", borderRadius: 8, textDecoration: "none",
                fontSize: 13, fontWeight: isToday ? 700 : 400, background: isToday ? "var(--color-accent)" : undefined, color: isToday ? "var(--color-on-accent)" : undefined }}>
              {i + 1}
              <span aria-hidden="true" style={{ width: 4, height: 4, borderRadius: 999, background: count ? (isToday ? "var(--color-on-accent)" : "var(--color-accent)") : "transparent" }} />
            </Link>
          );
        })}
      </div>
    </section>
  );
}
