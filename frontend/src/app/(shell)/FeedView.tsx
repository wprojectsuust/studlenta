"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";
import { CategoryIcon } from "@/components/CategoryIcon";
import { EventCard } from "@/components/EventCard";
import { EventStrip } from "@/components/EventStrip";
import { CardSkeleton, EmptyState, ErrorBanner, LoginToast, Toast } from "@/components/Feedback";
import { MiniCalendar } from "@/components/MiniCalendar";
import { PERIODS, PeriodFilter } from "@/components/PeriodFilter";
import type { FeedItem, Period } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useCategories, useFeed, useGuestFavorites, useReactions, useRecommendations, useUpcoming, withGuestFavorites } from "@/lib/queries";

const isPeriod = (v: string | null): v is Period => PERIODS.some((p) => p.id === v);

function plural(n: number) {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return "событие";
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return "события";
  return "событий";
}

export function FeedView() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { status } = useAuth();
  const reactions = useReactions();
  const categories = useCategories();

  const period: Period = isPeriod(params.get("period")) ? (params.get("period") as Period) : "all";
  const category = params.get("category");
  const q = params.get("q");
  const favorites = params.get("favorites") === "1";
  const guestFavorites = favorites && status === "guest";

  const feed = useFeed({ period, category, q, favorites: favorites && status === "authenticated" });
  const guestList = useGuestFavorites(guestFavorites);
  const loading = status === "loading" || (guestFavorites ? guestList.isPending : feed.isPending);
  const raw: FeedItem[] = guestFavorites ? (guestList.data ?? []) : (feed.data?.pages.flatMap((p) => p.items) ?? []);
  const items = withGuestFavorites(raw, reactions.isGuest);

  const sentinel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = sentinel.current;
    if (!node || !feed.hasNextPage) return;
    const io = new IntersectionObserver(([entry]) => entry?.isIntersecting && !feed.isFetchingNextPage && void feed.fetchNextPage());
    io.observe(node);
    return () => io.disconnect();
  }, [feed]);

  const setParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    router.replace(`${pathname}?${next}`, { scroll: false });
  };

  const home = !favorites && !q && !category && period === "all";
  const upcoming = useUpcoming(home);
  const recs = useRecommendations(home);
  // На холодном старте подборка совпала бы с «Ближайшими» — показываем её, только когда есть за что зацепиться.
  const personal = recs.data?.some((r) => r.reason_kind !== "soon") ? recs.data : [];
  const categoryName = categories.data?.find((c) => c.slug === category)?.name;
  const title = favorites ? "Избранное" : q ? `Поиск: «${q}»` : (categoryName ?? "Лента событий");

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 28, alignItems: "flex-start" }}>
      <section aria-labelledby="feed-title" style={{ flex: "999 1 560px", minWidth: 0, display: "flex", flexDirection: "column", gap: 16 }}>
        <h1 id="feed-title" className="page-title">{title}</h1>
        {home && <EventStrip title="Ближайшие" items={upcoming.data?.items ?? []} />}
        {home && personal && (
          <EventStrip
            title="Для вас"
            hint="По вашим просмотрам и избранному"
            items={personal}
            reasons={Object.fromEntries(personal.map((r) => [r.id, r.reason]))}
          />
        )}
        {home && (upcoming.data?.items.length ?? 0) > 0 && <h2 style={{ fontSize: 20, fontWeight: 700, marginTop: 8 }}>Все события</h2>}

        <nav aria-label="Категории" className="category-strip">
          <Link href="/" aria-current={!category && !favorites ? "page" : undefined} className="chip">Все</Link>
          {categories.data?.map((c) => (
            <Link key={c.id} href={`/?category=${c.slug}`} aria-current={category === c.slug ? "page" : undefined} className="chip">
              <CategoryIcon slug={c.slug} size={18} />
              {c.name}
            </Link>
          ))}
        </nav>

        {!favorites && <PeriodFilter value={period} onChange={(p) => setParam("period", p === "all" ? null : p)} />}

        <p aria-live="polite" className="sr-only">{loading ? "Загружаем события" : `Показано ${items.length} ${plural(items.length)}`}</p>

        {feed.isError && !guestFavorites && <ErrorBanner message="Не удалось загрузить события." onRetry={() => void feed.refetch()} />}
        {loading && [0, 1, 2].map((i) => <CardSkeleton key={i} />)}
        {!loading && items.length === 0 && (
          favorites ? (
            <EmptyState title="В избранном пусто">Нажмите на закладку у события, чтобы сохранить его.</EmptyState>
          ) : (
            <EmptyState title="Событий нет">Попробуйте другой период или категорию.</EmptyState>
          )
        )}
        {items.map((item, index) => (
          <EventCard key={item.id} item={item} priority={index < 2} onLike={() => void reactions.toggleLike(item)} onFavorite={() => void reactions.toggleFavorite(item)} />
        ))}
        {feed.hasNextPage && !guestFavorites && (
          <div ref={sentinel} style={{ display: "flex", justifyContent: "center" }}>
            <button type="button" className="btn btn-secondary" onClick={() => void feed.fetchNextPage()} disabled={feed.isFetchingNextPage}>
              {feed.isFetchingNextPage ? "Загружаем…" : "Показать ещё"}
            </button>
          </div>
        )}
      </section>

      <aside aria-label="Календарь" className="hide-mobile" style={{ flex: "1 1 280px", minWidth: 0, display: "flex", flexDirection: "column", gap: 20 }}>
        <MiniCalendar />
      </aside>

      {reactions.needsLogin && <LoginToast onClose={reactions.dismiss} />}
      {reactions.error && <Toast onClose={reactions.dismiss}>{reactions.error}</Toast>}
    </div>
  );
}
