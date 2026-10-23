"use client";

import { useInfiniteQuery, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { endpoints, type EventStatus, type FeedItem, type FeedParams } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { readGuestFavorites, toggleGuestFavorite } from "@/lib/guestFavorites";

export function useFeed(params: Omit<FeedParams, "cursor">) {
  return useInfiniteQuery({
    queryKey: ["feed", params],
    queryFn: ({ pageParam }) => endpoints.feed({ ...params, cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
  });
}

/** Подборка «Ближайшие» наверху ленты. */
export const useUpcoming = (enabled: boolean) =>
  useQuery({ queryKey: ["upcoming"], queryFn: () => endpoints.feed({ period: "all", limit: 10 }), enabled, staleTime: 15_000 });

export const useCategories = () => useQuery({ queryKey: ["categories"], queryFn: endpoints.categories, staleTime: 60_000 });
export const useCalendar = (month: string) => useQuery({ queryKey: ["calendar", month], queryFn: () => endpoints.calendar(month) });
export const useDay = (date: string) => useQuery({ queryKey: ["day", date], queryFn: () => endpoints.day(date) });
export const useSimilar = (id: string) => useQuery({ queryKey: ["similar", id], queryFn: () => endpoints.similar(id) });
export const useMyEvents = (status?: EventStatus) =>
  useQuery({ queryKey: ["me", "events", status ?? "all"], queryFn: () => endpoints.myEvents(status) });
export const useQueue = (status: EventStatus, enabled = true) =>
  useQuery({ queryKey: ["moderation", status], queryFn: () => endpoints.queue(status), enabled });
export const useHistory = (id: string | null) =>
  useQuery({ queryKey: ["history", id], queryFn: () => endpoints.history(id ?? ""), enabled: id !== null });

/** Избранное гостя — подтягиваем события по id из localStorage. */
export function useGuestFavorites(enabled: boolean) {
  return useQuery({
    queryKey: ["guest-favorites"],
    enabled,
    queryFn: async () => {
      const results = await Promise.allSettled(readGuestFavorites().map((id) => endpoints.event(id)));
      return results.flatMap((r) => (r.status === "fulfilled" ? [{ ...r.value, favorited: true }] : []));
    },
  });
}

/** Обходит любые закешированные структуры (страницы ленты, списки, одно событие) и правит событие. */
function patchEverywhere(client: QueryClient, id: string, fn: (item: FeedItem) => FeedItem) {
  const visit = (data: unknown): unknown => {
    if (Array.isArray(data)) return data.map(visit);
    if (data && typeof data === "object") {
      const obj = data as Record<string, unknown>;
      if (obj.id === id && "likes_count" in obj) return fn(obj as FeedItem);
      if (Array.isArray(obj.pages)) return { ...obj, pages: obj.pages.map(visit) };
      if (Array.isArray(obj.items)) return { ...obj, items: obj.items.map(visit) };
    }
    return data;
  };
  for (const key of ["feed", "event", "day", "similar", "guest-favorites", "upcoming"]) {
    client.setQueriesData({ queryKey: [key] }, visit);
  }
}

const SAVE_FAILED = "Не удалось сохранить, попробуйте ещё раз";

export function useReactions() {
  const client = useQueryClient();
  const { status } = useAuth();
  const isGuest = status !== "authenticated";
  const [needsLogin, setNeedsLogin] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleLike = useCallback(
    async (item: FeedItem) => {
      if (isGuest) return setNeedsLogin(true);
      const on = !item.liked;
      const apply = (liked: boolean) =>
        patchEverywhere(client, item.id, (i) => ({ ...i, liked, likes_count: i.likes_count + (liked === i.liked ? 0 : liked ? 1 : -1) }));
      apply(on);
      setError(null);
      try {
        await endpoints.like(item.id, on);
      } catch {
        apply(!on);
        setError(SAVE_FAILED);
      }
    },
    [client, isGuest],
  );

  const toggleFavorite = useCallback(
    async (item: FeedItem) => {
      if (isGuest) {
        const added = toggleGuestFavorite(item.id);
        patchEverywhere(client, item.id, (i) => ({ ...i, favorited: added }));
        void client.invalidateQueries({ queryKey: ["guest-favorites"] });
        return;
      }
      const on = !item.favorited;
      patchEverywhere(client, item.id, (i) => ({ ...i, favorited: on }));
      setError(null);
      try {
        await endpoints.favorite(item.id, on);
        void client.invalidateQueries({ queryKey: ["feed", { favorites: true }] });
      } catch {
        patchEverywhere(client, item.id, (i) => ({ ...i, favorited: !on }));
        setError(SAVE_FAILED);
      }
    },
    [client, isGuest],
  );

  return {
    isGuest,
    needsLogin,
    error,
    toggleLike,
    toggleFavorite,
    dismiss: () => {
      setNeedsLogin(false);
      setError(null);
    },
  };
}

/** Для гостя флаг «в избранном» берём из localStorage — сервер о нём не знает. */
export function withGuestFavorites(items: FeedItem[], isGuest: boolean): FeedItem[] {
  if (!isGuest) return items;
  const ids = new Set(readGuestFavorites());
  return items.map((i) => (ids.has(i.id) ? { ...i, favorited: true } : i));
}
