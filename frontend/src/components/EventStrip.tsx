"use client";

import Link from "next/link";
import { useId, useRef } from "react";
import type { FeedItem } from "@/lib/api";
import { formatWhen } from "@/lib/format";
import { Cover } from "./Cover";
import { ChevronLeft, ChevronRight } from "./icons";
import styles from "./EventStrip.module.css";

type Props = { title: string; hint?: string; items: FeedItem[]; reasons?: Record<string, string>; now?: Date };

/** Горизонтальная подборка карточек: «Ближайшие», «Для вас». Скролл пальцем, стрелками и Tab. */
export function EventStrip({ title, hint, items, reasons, now = new Date() }: Props) {
  const id = useId();
  const list = useRef<HTMLUListElement>(null);
  if (items.length === 0) return null;

  const scroll = (dir: 1 | -1) => {
    const el = list.current;
    if (el) el.scrollBy({ left: dir * Math.max(el.clientWidth * 0.8, 260) });
  };

  return (
    <section className={styles.strip} aria-labelledby={`${id}-title`}>
      <div className={styles.head}>
        <h2 id={`${id}-title`}>{title}{hint && <small>{hint}</small>}</h2>
        <button type="button" className={styles.arrow} aria-label="Прокрутить назад" onClick={() => scroll(-1)}><ChevronLeft size={18} /></button>
        <button type="button" className={styles.arrow} aria-label="Прокрутить вперёд" onClick={() => scroll(1)}><ChevronRight size={18} /></button>
      </div>
      <ul ref={list} className={styles.list}>
        {items.map((item, index) => (
          <li key={item.id} className={styles.item}>
            <Link href={`/events/${item.id}`} className={styles.card}>
              <div className={styles.media}>
                <Cover src={item.cover_url} category={item.category} sizes="260px" priority={index < 3} />
                <span className={styles.when}>{formatWhen(item.starts_at, now)}</span>
              </div>
              <div className={styles.body}>
                <span className={styles.title}>{item.title}</span>
                <span className={styles.meta}>{item.category.name} · {item.place}</span>
                {reasons?.[item.id] && <span className={styles.reason}>{reasons[item.id]}</span>}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
