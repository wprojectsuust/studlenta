-- Схема Студленты. Статусы и роли — enum'ы БД, чтобы мусор не попал даже мимо приложения.

CREATE TYPE user_role AS ENUM ('author', 'moderator', 'admin');
CREATE TYPE event_status AS ENUM (
    'draft', 'pending', 'changes_requested', 'published', 'rejected', 'archived'
);
CREATE TYPE moderation_action AS ENUM (
    'submitted', 'withdrawn', 'approved', 'changes_requested', 'rejected', 'archived'
);
CREATE TYPE notification_kind AS ENUM ('approved', 'changes_requested', 'rejected', 'reminder');

CREATE TABLE users (
    id            uuid PRIMARY KEY,
    email         text NOT NULL UNIQUE CHECK (email = lower(email)),
    full_name     text NOT NULL CHECK (length(full_name) BETWEEN 1 AND 120),
    role          user_role NOT NULL DEFAULT 'author',
    password_hash text NOT NULL,
    created_at    timestamptz NOT NULL
);

CREATE TABLE categories (
    id       smallint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug     text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9][a-z0-9-]{0,39}$'),
    name     text NOT NULL,
    -- Только палитра с контрастом белого текста >= 4.5:1 (см. domain/categories.py).
    color    char(7) NOT NULL CHECK (color IN (
        '#7C3AED', '#15803D', '#1D4ED8', '#C2410C', '#BE185D', '#0E7490', '#4B5563'
    )),
    position smallint NOT NULL DEFAULT 0
);

CREATE TABLE events (
    id             uuid PRIMARY KEY,
    author_id      uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    category_id    smallint REFERENCES categories (id),
    title          text NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
    summary        text NOT NULL DEFAULT '' CHECK (length(summary) <= 200),
    body           text NOT NULL DEFAULT '' CHECK (length(body) <= 10000),
    place          text NOT NULL DEFAULT '' CHECK (length(place) <= 200),
    starts_at      timestamptz,
    ends_at        timestamptz,
    cover_url      text,
    status         event_status NOT NULL,
    moderator_note text,
    created_at     timestamptz NOT NULL,
    updated_at     timestamptz NOT NULL,
    submitted_at   timestamptz,
    published_at   timestamptz,
    version        integer NOT NULL DEFAULT 1,
    -- Всё, что ушло из черновика, обязано иметь дату и категорию.
    CONSTRAINT events_submitted_complete CHECK (
        status = 'draft' OR (starts_at IS NOT NULL AND category_id IS NOT NULL)
    ),
    CONSTRAINT events_end_after_start CHECK (ends_at IS NULL OR ends_at > starts_at),
    CONSTRAINT events_published_has_date CHECK (
        status NOT IN ('published', 'archived') OR published_at IS NOT NULL
    ),
    search tsvector GENERATED ALWAYS AS (
        to_tsvector('russian', title || ' ' || summary)
    ) STORED
);

CREATE INDEX events_feed_idx ON events (starts_at, id) WHERE status = 'published';
CREATE INDEX events_category_feed_idx ON events (category_id, starts_at, id)
    WHERE status = 'published';
CREATE INDEX events_search_idx ON events USING gin (search);
CREATE INDEX events_author_idx ON events (author_id, updated_at DESC);
CREATE INDEX events_queue_idx ON events (status, submitted_at, id);

CREATE TABLE likes (
    user_id    uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    event_id   uuid NOT NULL REFERENCES events (id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (user_id, event_id)
);
CREATE INDEX likes_event_idx ON likes (event_id);

CREATE TABLE favorites (
    user_id    uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    event_id   uuid NOT NULL REFERENCES events (id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (user_id, event_id)
);
CREATE INDEX favorites_event_idx ON favorites (event_id);

CREATE TABLE moderation_log (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id   uuid NOT NULL REFERENCES events (id) ON DELETE CASCADE,
    actor_id   uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    action     moderation_action NOT NULL,
    note       text,
    created_at timestamptz NOT NULL
);
CREATE INDEX moderation_log_event_idx ON moderation_log (event_id, created_at DESC);

CREATE TABLE notifications (
    id         uuid PRIMARY KEY,
    user_id    uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    kind       notification_kind NOT NULL,
    event_id   uuid NOT NULL REFERENCES events (id) ON DELETE CASCADE,
    text       text NOT NULL,
    created_at timestamptz NOT NULL,
    read_at    timestamptz
);
CREATE INDEX notifications_inbox_idx ON notifications (user_id, created_at DESC);
CREATE UNIQUE INDEX notifications_one_reminder ON notifications (user_id, event_id)
    WHERE kind = 'reminder';

CREATE TABLE refresh_tokens (
    token_hash text PRIMARY KEY,
    user_id    uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz
);
CREATE INDEX refresh_tokens_user_idx ON refresh_tokens (user_id);
