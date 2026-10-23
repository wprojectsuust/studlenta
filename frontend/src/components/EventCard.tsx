import Link from "next/link";
import type { FeedItem } from "@/lib/api";
import { formatWhen, isToday } from "@/lib/format";
import { Cover } from "./Cover";
import { BookmarkIcon, CalendarIcon, HeartIcon, PinIcon } from "./icons";
import { TagPill } from "./TagPill";
import styles from "./EventCard.module.css";

type Props = { item: FeedItem; now?: Date; onLike: () => void; onFavorite: () => void; priority?: boolean };

export function EventCard({ item, now = new Date(), onLike, onFavorite, priority = false }: Props) {
  return (
    <article className={styles.card} aria-labelledby={`t-${item.id}`}>
      <div className={styles.media}>
        <Cover src={item.cover_url} category={item.category} sizes="(max-width: 760px) 100vw, 220px" priority={priority} />
        {isToday(item.starts_at, now) && (
          <span className={styles.badge} data-badge>
            Сегодня
          </span>
        )}
      </div>
      <div className={styles.body}>
        <div className={styles.meta}>
          <TagPill category={item.category} />
          <span>
            <CalendarIcon size={15} />
            {formatWhen(item.starts_at, now)}
          </span>
          <span>
            <PinIcon size={15} />
            {item.place}
          </span>
        </div>
        <h2 className={styles.title} id={`t-${item.id}`}>
          <Link href={`/events/${item.id}`}>{item.title}</Link>
        </h2>
        <p className={styles.summary}>{item.summary}</p>
        <div className={styles.actions}>
          <button type="button" className={`${styles.action} ${item.liked ? styles.liked : ""}`} aria-pressed={item.liked}
            aria-label={`Нравится, ${item.likes_count}`} onClick={onLike}>
            <HeartIcon size={18} fill={item.liked ? "currentColor" : "none"} />
            <span aria-hidden="true">{item.likes_count}</span>
          </button>
          <button type="button" className={`${styles.action} ${item.favorited ? styles.faved : ""}`} aria-pressed={item.favorited}
            aria-label={item.favorited ? "Убрать из избранного" : "Добавить в избранное"} onClick={onFavorite}>
            <BookmarkIcon size={18} fill={item.favorited ? "currentColor" : "none"} />
            {item.favorited && <span aria-hidden="true">В избранном</span>}
          </button>
        </div>
      </div>
    </article>
  );
}
