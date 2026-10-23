"use client";

import Link from "next/link";
import { useState } from "react";
import { CategoryIcon } from "@/components/CategoryIcon";
import { CardSkeleton, EmptyState, ErrorBanner } from "@/components/Feedback";
import type { InterestReport } from "@/lib/api";
import { formatWhen } from "@/lib/format";
import { useInterestAnalytics } from "@/lib/queries";
import { useRequireAuth } from "@/lib/useRequireAuth";
import styles from "./analytics.module.css";

const RANGES = [7, 30, 90] as const;
const number = new Intl.NumberFormat("ru-RU", { notation: "compact", maximumFractionDigits: 1 });
const dayLabel = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short", timeZone: "UTC" });
const day = (iso: string) => dayLabel.format(new Date(`${iso}T00:00:00Z`));

export function AnalyticsView() {
  const auth = useRequireAuth();
  const [days, setDays] = useState<(typeof RANGES)[number]>(30);
  const report = useInterestAnalytics(days, auth.status === "authenticated");

  return (
    <div className={styles.page}>
      <h1 className="page-title">Аналитика интересов</h1>
      <p className={styles.lead}>
        {report.data?.scope === "mine"
          ? "Как студенты откликаются на ваши события: просмотры, лайки и избранное."
          : "Что интересует студентов: просмотры, лайки и избранное по всей ленте."}{" "}
        Просмотр считается один раз в день на человека; гости — по анонимному id браузера.
      </p>
      <div role="group" aria-label="Период" className={styles.ranges}>
        {RANGES.map((d) => (
          <button key={d} type="button" className="btn" aria-pressed={d === days} onClick={() => setDays(d)}>
            {d} дней
          </button>
        ))}
      </div>
      {report.error && <ErrorBanner message="Не удалось загрузить аналитику" onRetry={() => void report.refetch()} />}
      {!report.data && !report.error && <CardSkeleton />}
      {report.data && <Report data={report.data} />}
    </div>
  );
}

export function Report({ data }: { data: InterestReport }) {
  if (data.totals.views + data.totals.likes + data.totals.favorites === 0) {
    return (
      <EmptyState title="Пока тихо">
        За этот период событий не смотрели. <Link href="/">Открыть ленту</Link>
      </EmptyState>
    );
  }
  const tiles = [
    ["Просмотры", data.totals.views],
    ["Зрители", data.totals.viewers],
    ["Лайки", data.totals.likes],
    ["В избранном", data.totals.favorites],
  ] as const;
  return (
    <>
      <ul className={styles.tiles} aria-label="Итоги за период">
        {tiles.map(([label, value]) => (
          <li key={label} className="card">
            <span className={styles.tileLabel}>{label}</span>
            <strong className={styles.tileValue}>{number.format(value)}</strong>
          </li>
        ))}
      </ul>
      <DailyChart data={data} />
      <Categories data={data} />
      <TopEvents data={data} />
    </>
  );
}

/** Столбики просмотров по дням: одна серия, цвет акцента скина, подсказка при наведении. */
function DailyChart({ data }: { data: InterestReport }) {
  const [first, ...rest] = data.daily;
  if (!first) return null;
  const last = rest.at(-1) ?? first;
  const max = Math.max(...data.daily.map((d) => d.views), 1);
  const peak = rest.reduce((a, b) => (b.views > a.views ? b : a), first);
  const ticks = [max, Math.round(max / 2), 0].filter((v, i, all) => all.indexOf(v) === i);
  return (
    <section className={`card ${styles.section}`} aria-labelledby="daily-title">
      <h2 id="daily-title">Просмотры по дням</h2>
      <p className={styles.note}>Пик — {day(peak.day)}: {peak.views} просмотров</p>
      <div className={styles.chart} role="img" aria-label={`Просмотры по дням, максимум ${peak.views} — ${day(peak.day)}. Значения — в таблице ниже.`}>
        <div className={styles.axis} aria-hidden>
          {ticks.map((t) => <span key={t} style={{ bottom: `${(t / max) * 100}%` }}>{number.format(t)}</span>)}
        </div>
        <div className={styles.plot} aria-hidden>
          {ticks.map((t) => <i key={t} className={styles.grid} style={{ bottom: `${(t / max) * 100}%` }} />)}
          {data.daily.map((d) => (
            <div key={d.day} className={styles.slot}>
              <div className={styles.column} style={{ height: `${(d.views / max) * 100}%` }} />
              <span className={styles.tip}>{day(d.day)}<b>{d.views} просм. · {d.viewers} чел.</b></span>
            </div>
          ))}
        </div>
      </div>
      <div className={styles.dates} aria-hidden>
        <span>{day(first.day)}</span>
        <span>{day(last.day)}</span>
      </div>
      <details className={styles.table}>
        <summary>Таблица по дням</summary>
        <table>
          <thead><tr><th scope="col">День</th><th scope="col">Просмотры</th><th scope="col">Зрители</th></tr></thead>
          <tbody>
            {data.daily.map((d) => <tr key={d.day}><th scope="row">{day(d.day)}</th><td>{d.views}</td><td>{d.viewers}</td></tr>)}
          </tbody>
        </table>
      </details>
    </section>
  );
}

/** Категории по просмотрам: горизонтальные полосы одного цвета, значение у конца полосы. */
function Categories({ data }: { data: InterestReport }) {
  const max = Math.max(...data.categories.map((c) => c.views), 1);
  return (
    <section className={`card ${styles.section}`} aria-labelledby="cat-title">
      <h2 id="cat-title">Интерес по категориям</h2>
      <ul className={styles.bars}>
        {data.categories.map((c) => (
          <li key={c.category.id}>
            <span className={styles.barLabel}><CategoryIcon slug={c.category.slug} size={18} />{c.category.name}</span>
            <span className={styles.barTrack}>
              <span className={styles.bar} style={{ width: `${(c.views / max) * 100}%` }} />
              <span className={styles.barValue}>{c.views}</span>
            </span>
            <span className={styles.barMeta}>лайки {c.likes} · в избранном {c.favorites} · событий {c.events}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function TopEvents({ data }: { data: InterestReport }) {
  if (data.top.length === 0) return null;
  return (
    <section className={`card ${styles.section}`} aria-labelledby="top-title">
      <h2 id="top-title">Самые интересные события</h2>
      <div className={styles.scroll}>
        <table className={styles.top}>
          <thead>
            <tr>
              <th scope="col">Событие</th>
              <th scope="col">Просмотры</th>
              <th scope="col">Зрители</th>
              <th scope="col">Лайки</th>
              <th scope="col">Избранное</th>
              <th scope="col">Конверсия в избранное</th>
            </tr>
          </thead>
          <tbody>
            {data.top.map((e) => (
              <tr key={e.id}>
                <th scope="row">
                  <Link href={`/events/${e.id}`}>{e.title}</Link>
                  <small>{e.category.name} · {formatWhen(e.starts_at)}</small>
                </th>
                <td>{e.views}</td>
                <td>{e.viewers}</td>
                <td>{e.likes}</td>
                <td>{e.favorites}</td>
                <td>{e.viewers ? `${Math.round((e.favorites / e.viewers) * 100)}%` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
