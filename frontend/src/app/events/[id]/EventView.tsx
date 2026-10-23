"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useState, useSyncExternalStore } from "react";

const noSubscribe = () => () => undefined;
import { Cover } from "@/components/Cover";
import { EmptyState, LoginToast, Toast } from "@/components/Feedback";
import { BookmarkIcon, CalendarIcon, HeartIcon, LinkIcon, PinIcon, ShieldIcon, TicketIcon, UserIcon } from "@/components/icons";
import { TagPill } from "@/components/TagPill";
import { API_BASE } from "@/lib/config";
import { ApiError, endpoints, type EventDetails } from "@/lib/api";
import { formatTime, formatWhen, formatWhenInline } from "@/lib/format";
import { useReactions, useSimilar, withGuestFavorites } from "@/lib/queries";
import { visitorId } from "@/lib/visitor";
import styles from "./event.module.css";

export function EventView({ initial }: { initial: EventDetails }) {
  // Сервер отдал публичные данные; клиент дозапрашивает флаги «лайкнул / в избранном» для текущего пользователя.
  const query = useQuery({ queryKey: ["event", initial.id], queryFn: () => endpoints.event(initial.id), initialData: initial, initialDataUpdatedAt: 0 });
  const reactions = useReactions();
  const similar = useSimilar(initial.id);
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    // Сигнал интереса для «Для вас» и аналитики; ошибка не мешает читать событие.
    endpoints.recordView(initial.id, visitorId()).catch(() => undefined);
  }, [initial.id]);
  const url = useSyncExternalStore(noSubscribe, () => window.location.href, () => "");

  if (query.error instanceof ApiError && query.error.status === 404) {
    return <EmptyState title="Событие недоступно">Его сняли с публикации. <Link href="/">Вернуться в ленту</Link></EmptyState>;
  }
  const [event] = withGuestFavorites([query.data], reactions.isGuest) as [EventDetails];
  const paragraphs = event.body.split(/\n{2,}/);

  async function copy() {
    await navigator.clipboard?.writeText(url).catch(() => undefined);
    setCopied(true);
  }

  return (
    <div className={styles.layout}>
      <article className={`card ${styles.article}`} aria-labelledby="event-title">
        <Cover src={event.cover_url} category={event.category} alt={`Обложка: ${event.title}`} className={styles.hero}
          sizes="(max-width: 760px) 100vw, 900px" priority />
        <div className={styles.head}>
          <div className={styles.meta}>
            <TagPill category={event.category} />
            <span>{formatWhen(event.starts_at)}</span>
            <span>{event.place}</span>
          </div>
          <h1 id="event-title" className={styles.title}>{event.title}</h1>
          <p className={styles.lead}>{event.summary}</p>
        </div>

        <dl className={styles.tiles}>
          <div><CalendarIcon /><dt className="sr-only">Когда</dt><dd><strong>{formatWhen(event.starts_at)}</strong>{event.ends_at && <span>до {formatTime(event.ends_at)}</span>}</dd></div>
          <div><PinIcon /><dt className="sr-only">Где</dt><dd><strong>{event.place}</strong></dd></div>
          <div><TicketIcon /><dt className="sr-only">Организатор</dt><dd><strong>{event.organizer_name}</strong><span>Организатор</span></dd></div>
        </dl>

        <div className={styles.actions}>
          <a className="btn btn-primary" href={`${API_BASE}/events/${event.id}/ics`} download>
            <CalendarIcon size={18} />Добавить в календарь
          </a>
          <button type="button" className="btn btn-secondary" aria-pressed={event.liked} aria-label={`Нравится, ${event.likes_count}`}
            onClick={() => void reactions.toggleLike(event)} style={{ color: event.liked ? "var(--color-like)" : undefined }}>
            <HeartIcon size={18} fill={event.liked ? "currentColor" : "none"} /><span aria-hidden="true">{event.likes_count}</span>
          </button>
          <button type="button" className="btn btn-secondary" aria-pressed={event.favorited} onClick={() => void reactions.toggleFavorite(event)}
            style={{ color: event.favorited ? "var(--color-fav)" : undefined }}>
            <BookmarkIcon size={18} fill={event.favorited ? "currentColor" : "none"} />{event.favorited ? "В избранном" : "В избранное"}
          </button>
        </div>

        <section className={styles.body} aria-labelledby="about-title">
          <h2 id="about-title">О событии</h2>
          {paragraphs.map((p, i) => <p key={i}>{p}</p>)}
        </section>

        <div className={styles.share}>
          <span>Поделиться</span>
          <a className="btn btn-ghost" href={`https://vk.com/share.php?url=${encodeURIComponent(url)}`} target="_blank" rel="noopener noreferrer">ВКонтакте</a>
          <a className="btn btn-ghost" href={`https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(event.title)}`} target="_blank" rel="noopener noreferrer">Telegram</a>
          <button type="button" className="btn btn-ghost" onClick={() => void copy()}><LinkIcon size={18} />Ссылка</button>
          <span role="status" className={copied ? undefined : "sr-only"}>{copied ? "Ссылка скопирована" : ""}</span>
        </div>
      </article>

      <aside className={styles.aside} aria-label="Дополнительно">
        <section className="card" style={{ padding: 20, display: "flex", gap: 12, alignItems: "center" }}>
          <span style={{ width: 48, height: 48, borderRadius: 12, background: "var(--color-accent)", color: "var(--color-on-accent)", display: "grid", placeItems: "center" }}><UserIcon /></span>
          <span><strong style={{ display: "block" }}>{event.organizer_name}</strong><span style={{ fontSize: 13, color: "var(--color-muted)" }}>Организатор</span></span>
        </section>
        <p className={styles.verified}><ShieldIcon size={18} />Проверено модератором {formatWhenInline(event.published_at)}</p>
        <section className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }} aria-labelledby="similar-title">
          <h2 id="similar-title" style={{ fontSize: 15 }}>Похожие события</h2>
          {similar.data?.length === 0 && <p style={{ fontSize: 14, color: "var(--color-muted)" }}>Пока нет других событий в этой категории.</p>}
          {similar.data?.map((s) => (
            <Link key={s.id} href={`/events/${s.id}`} style={{ display: "flex", gap: 12, alignItems: "center", textDecoration: "none" }}>
              <Cover src={s.cover_url} category={s.category} sizes="56px" style={{ width: 56, height: 56, borderRadius: 10, flex: "none" }} />
              <span><strong style={{ display: "block", fontSize: 14 }}>{s.title}</strong><span style={{ fontSize: 13, color: "var(--color-muted)" }}>{formatWhen(s.starts_at)} · {s.place}</span></span>
            </Link>
          ))}
        </section>
      </aside>
      {reactions.needsLogin && <LoginToast onClose={reactions.dismiss} />}
      {reactions.error && <Toast onClose={reactions.dismiss}>{reactions.error}</Toast>}
    </div>
  );
}
