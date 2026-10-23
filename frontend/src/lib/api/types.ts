// Зеркало схем бэкенда (backend/src/studlenta/presentation/api/schemas.py).

export type Role = "author" | "moderator" | "admin";
export type EventStatus = "draft" | "pending" | "changes_requested" | "published" | "rejected" | "archived";
export type Period = "all" | "today" | "week" | "month";

export type Category = { id: number; slug: string; name: string; color: string };
export type CategoryCount = Category & { upcoming_count: number };

export type FeedItem = {
  id: string;
  title: string;
  summary: string;
  place: string;
  starts_at: string;
  ends_at: string | null;
  cover_url: string | null;
  category: Category;
  likes_count: number;
  liked: boolean;
  favorited: boolean;
};
export type Page = { items: FeedItem[]; next_cursor: string | null };
export type EventDetails = FeedItem & { body: string; organizer_name: string; published_at: string };

export type MyEvent = {
  id: string;
  title: string;
  status: EventStatus;
  cover_url: string | null;
  starts_at: string | null;
  updated_at: string;
  moderator_note: string | null;
  likes_count: number;
  favorites_count: number;
};

export type AuthoredEvent = {
  id: string;
  author_id: string;
  author_name: string;
  status: EventStatus;
  title: string;
  summary: string;
  body: string;
  category: Category | null;
  place: string;
  starts_at: string | null;
  ends_at: string | null;
  cover_url: string | null;
  moderator_note: string | null;
  submitted_at: string | null;
  updated_at: string;
  is_resubmission: boolean;
};

export type EventInput = {
  title: string;
  summary: string;
  body: string;
  category_id: number | null;
  place: string;
  starts_at: string | null;
  ends_at: string | null;
  cover_url: string | null;
};

export type HistoryEntry = {
  action: "submitted" | "withdrawn" | "approved" | "changes_requested" | "rejected" | "archived";
  note: string | null;
  created_at: string;
  actor_name: string;
};
export type CalendarDay = { date: string; count: number; preview: { title: string; color: string }[] };
export type Notification = {
  id: string;
  kind: "approved" | "changes_requested" | "rejected" | "reminder";
  event_id: string;
  text: string;
  created_at: string;
  read_at: string | null;
};
export type Inbox = { items: Notification[]; unread: number };
export type Profile = { id: string; email: string; full_name: string; role: Role; unread_notifications: number; email_verified: boolean };
export type Token = { access_token: string; token_type: string; expires_in: number };

export const canModerate = (role: Role | undefined) => role === "moderator" || role === "admin";
