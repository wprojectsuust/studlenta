-- Просмотры событий — сигнал интереса для рекомендаций и аналитики (ADR-0014).
-- Один просмотр на зрителя в день; зритель — аккаунт (u:) или анонимный id браузера (g:).
CREATE TABLE event_views (
    event_id  uuid NOT NULL REFERENCES events (id) ON DELETE CASCADE,
    viewer    text NOT NULL CHECK (viewer ~ '^[ug]:[0-9a-f-]{36}$'),
    user_id   uuid REFERENCES users (id) ON DELETE CASCADE,
    viewed_on date NOT NULL,
    viewed_at timestamptz NOT NULL,
    PRIMARY KEY (event_id, viewer, viewed_on)
);
CREATE INDEX event_views_viewer_idx ON event_views (viewer, viewed_at DESC);
CREATE INDEX event_views_time_idx ON event_views (viewed_at);
