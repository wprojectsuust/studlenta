import type { FeedItem, Profile } from "@/lib/api";

export const profile: Profile = { id: "u1", email: "anna@uust.ru", full_name: "Анна Смирнова", role: "author", unread_notifications: 2, email_verified: true };

export function feedItem(overrides: Partial<FeedItem> = {}): FeedItem {
  return {
    id: "e1",
    title: "Вечер студенческой музыки",
    summary: "Живой звук и любимые хиты",
    place: "Актовый зал УУНиТ",
    starts_at: "2026-10-23T13:00:00Z",
    ends_at: null,
    cover_url: "/studlenta/media/covers/a.jpg",
    category: { id: 1, slug: "concerts", name: "Концерты", color: "#7C3AED" },
    likes_count: 42,
    liked: false,
    favorited: false,
    ...overrides,
  };
}
