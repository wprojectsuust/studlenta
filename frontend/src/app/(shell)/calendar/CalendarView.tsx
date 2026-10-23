"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useRef, type KeyboardEvent } from "react";
import { CategoryIcon } from "@/components/CategoryIcon";
import { EventCard } from "@/components/EventCard";
import { EmptyState, LoginToast } from "@/components/Feedback";
import { ChevronLeft, ChevronRight } from "@/components/icons";
import { dayKey, formatDayTitle, monthTitle } from "@/lib/format";
import { useCalendar, useCategories, useDay, useReactions, withGuestFavorites } from "@/lib/queries";
import styles from "./calendar.module.css";

const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"];
const VALID = /^\d{4}-\d{2}-\d{2}$/;

function shiftMonth(year: number, month: number, delta: number) {
  const d = new Date(Date.UTC(year, month - 1 + delta, 1));
  return [d.getUTCFullYear(), d.getUTCMonth() + 1] as const;
}
const pad = (n: number) => String(n).padStart(2, "0");
function plural(n: number) {
  const a = n % 10, b = n % 100;
  return a === 1 && b !== 11 ? "событие" : a >= 2 && a <= 4 && (b < 12 || b > 14) ? "события" : "событий";
}

export function CalendarView() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const today = dayKey(new Date());
  const raw = params.get("date");
  const selected = raw && VALID.test(raw) ? raw : today;
  const [year, month] = selected.split("-").map(Number) as [number, number];
  const monthKey = `${year}-${pad(month)}`;
  const calendar = useCalendar(monthKey);
  const day = useDay(selected);
  const categories = useCategories();
  const reactions = useReactions();
  const grid = useRef<HTMLDivElement>(null);

  const byDate = new Map(calendar.data?.map((d) => [d.date, d]));
  const lead = (new Date(Date.UTC(year, month - 1, 1)).getUTCDay() + 6) % 7;
  const days = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const select = (date: string, focus = false) => {
    router.replace(`${pathname}?date=${date}`, { scroll: false });
    if (focus) requestAnimationFrame(() => grid.current?.querySelector<HTMLButtonElement>(`[data-date="${date}"]`)?.focus());
  };
  const goMonth = (delta: number) => {
    const [y, m] = shiftMonth(year, month, delta);
    select(`${y}-${pad(m)}-01`);
  };

  // Стрелки — по дням, PageUp/PageDown — по месяцам (handoff §3, CalendarMonth).
  function onKey(e: KeyboardEvent) {
    const steps: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };
    const base = new Date(`${selected}T12:00:00Z`);
    if (e.key in steps) base.setUTCDate(base.getUTCDate() + (steps[e.key] ?? 0));
    else if (e.key === "PageUp" || e.key === "PageDown") base.setUTCMonth(base.getUTCMonth() + (e.key === "PageUp" ? -1 : 1));
    else return;
    e.preventDefault();
    select(base.toISOString().slice(0, 10), true);
  }

  const items = withGuestFavorites(day.data ?? [], reactions.isGuest);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "12px 20px" }}>
        <h1 className="page-title" style={{ flex: "1 1 auto" }}>Календарь</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button type="button" className="btn btn-secondary" aria-label="Предыдущий месяц" onClick={() => goMonth(-1)} style={{ padding: 0, width: 44 }}><ChevronLeft size={18} /></button>
          <strong aria-live="polite" style={{ minWidth: 150, textAlign: "center", fontSize: 17 }}>{monthTitle(year, month)}</strong>
          <button type="button" className="btn btn-secondary" aria-label="Следующий месяц" onClick={() => goMonth(1)} style={{ padding: 0, width: 44 }}><ChevronRight size={18} /></button>
          <button type="button" className="btn btn-secondary" onClick={() => select(today)}>Сегодня</button>
        </div>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 24, alignItems: "flex-start" }}>
        <div className="card" style={{ flex: "999 1 600px", minWidth: 0, padding: 8, overflowX: "auto" }}>
          <div ref={grid} role="grid" aria-label={`События, ${monthTitle(year, month)}`} className={styles.grid} onKeyDown={onKey}>
            <div role="row" className={styles.row}>
              {WEEKDAYS.map((w) => <div role="columnheader" key={w} className={styles.weekday}>{w}</div>)}
            </div>
            {Array.from({ length: Math.ceil((lead + days) / 7) }, (_, row) => (
              <div role="row" key={row} className={styles.row}>
                {Array.from({ length: 7 }, (_, col) => {
                  const n = row * 7 + col - lead + 1;
                  if (n < 1 || n > days) return <div role="gridcell" key={col} />;
                  const date = `${monthKey}-${pad(n)}`;
                  const info = byDate.get(date);
                  const on = date === selected;
                  return (
                    <div role="gridcell" key={col} aria-selected={on}>
                      {/* Имя кнопки = видимый текст + скрытое уточнение, без aria-label поверх (WCAG 2.5.3) */}
                      <button type="button" data-date={date} tabIndex={on ? 0 : -1} onClick={() => select(date)}
                        className={`${styles.day} ${on ? styles.selected : ""} ${date === today ? styles.today : ""}`}>
                        <span className={styles.num}>{n}</span>
                        <span className="sr-only">{` ${MONTHS_GEN[month - 1]}${date === today ? ", сегодня" : ""}, ${info ? `${info.count} ${plural(info.count)}:` : "нет событий"}`}</span>
                        {info?.preview.map((p) => (
                          <span key={p.title} className={styles.pill} style={{ background: p.color }}>{p.title}</span>
                        ))}
                        {info && info.count > info.preview.length && <span className={styles.more}>ещё {info.count - info.preview.length}</span>}
                      </button>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        <section aria-labelledby="day-title" aria-live="polite" style={{ flex: "1 1 320px", minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
          <h2 id="day-title" style={{ fontSize: 18 }}>{formatDayTitle(selected)}</h2>
          {day.data?.length === 0 && <EmptyState title="В этот день событий нет" />}
          {items.map((item) => (
            <EventCard key={item.id} item={item} onLike={() => void reactions.toggleLike(item)} onFavorite={() => void reactions.toggleFavorite(item)} />
          ))}
        </section>
      </div>

      <ul aria-label="Цвета категорий" style={{ display: "flex", flexWrap: "wrap", gap: "8px 16px", margin: 0, padding: 0, listStyle: "none", fontSize: 13, color: "var(--color-muted)" }}>
        {categories.data?.map((c) => (
          <li key={c.id} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <CategoryIcon slug={c.slug} color={c.color} size={18} />{c.name}
          </li>
        ))}
      </ul>
      {reactions.needsLogin && <LoginToast onClose={reactions.dismiss} />}
    </div>
  );
}
