import { API_BASE } from "@/lib/config";
import { createApiClient } from "./client";
import type {
  AuthoredEvent, CalendarDay, CategoryCount, EventDetails, EventInput, EventStatus, FeedItem,
  HistoryEntry, Inbox, MyEvent, Page, Period, Profile, Token,
} from "./types";

export { ApiError } from "./client";
export type { FieldErrors } from "./client";
export * from "./types";

const authLostListeners = new Set<() => void>();
export const onAuthLost = (fn: () => void) => {
  authLostListeners.add(fn);
  return () => void authLostListeners.delete(fn);
};

export const api = createApiClient({
  baseUrl: API_BASE,
  onAuthLost: () => authLostListeners.forEach((fn) => fn()),
});

export type FeedParams = { period?: Period; category?: string | null; q?: string | null; favorites?: boolean; cursor?: string | null };

export const endpoints = {
  register: (body: { email: string; password: string; full_name: string }) =>
    api.request<Token>("/auth/register", { method: "POST", body }),
  login: (body: { email: string; password: string }) => api.request<Token>("/auth/login", { method: "POST", body }),
  logout: () => api.request<void>("/auth/logout", { method: "POST" }),
  me: () => api.request<Profile>("/me"),

  feed: (p: FeedParams) =>
    api.request<Page>("/events", { query: { period: p.period, category: p.category, q: p.q, favorites: p.favorites || undefined, cursor: p.cursor } }),
  event: (id: string) => api.request<EventDetails>(`/events/${id}`),
  similar: (id: string) => api.request<FeedItem[]>(`/events/${id}/similar`),
  categories: () => api.request<CategoryCount[]>("/categories"),
  calendar: (month: string) => api.request<CalendarDay[]>("/calendar", { query: { month } }),
  day: (date: string) => api.request<FeedItem[]>("/calendar/day", { query: { date } }),

  like: (id: string, on: boolean) => api.request<void>(`/events/${id}/like`, { method: on ? "PUT" : "DELETE" }),
  favorite: (id: string, on: boolean) => api.request<void>(`/events/${id}/favorite`, { method: on ? "PUT" : "DELETE" }),
  syncFavorites: (event_ids: string[]) => api.request<{ added: number }>("/me/favorites/sync", { method: "POST", body: { event_ids } }),

  myEvents: (status?: EventStatus) => api.request<MyEvent[]>("/me/events", { query: { status } }),
  myEvent: (id: string) => api.request<AuthoredEvent>(`/me/events/${id}`),
  createEvent: (body: EventInput) => api.request<{ id: string }>("/me/events", { method: "POST", body }),
  updateEvent: (id: string, body: EventInput) => api.request<void>(`/me/events/${id}`, { method: "PUT", body }),
  deleteEvent: (id: string) => api.request<void>(`/me/events/${id}`, { method: "DELETE" }),
  submit: (id: string) => api.request<void>(`/me/events/${id}/submit`, { method: "POST" }),
  withdraw: (id: string) => api.request<void>(`/me/events/${id}/withdraw`, { method: "POST" }),
  archive: (id: string) => api.request<void>(`/events/${id}/archive`, { method: "POST" }),
  history: (id: string) => api.request<HistoryEntry[]>(`/events/${id}/history`),
  uploadCover: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.request<{ url: string }>("/uploads/cover", { method: "POST", body: form });
  },

  queue: (status: EventStatus) => api.request<AuthoredEvent[]>("/moderation/queue", { query: { status } }),
  approve: (id: string) => api.request<void>(`/moderation/events/${id}/approve`, { method: "POST" }),
  requestChanges: (id: string, note: string) =>
    api.request<void>(`/moderation/events/${id}/request-changes`, { method: "POST", body: { note } }),
  reject: (id: string, note: string) => api.request<void>(`/moderation/events/${id}/reject`, { method: "POST", body: { note } }),

  inbox: () => api.request<Inbox>("/me/notifications"),
  markRead: (ids: string[] | null) => api.request<void>("/me/notifications/read", { method: "POST", body: { ids } }),
};
