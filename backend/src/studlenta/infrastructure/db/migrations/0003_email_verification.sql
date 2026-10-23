-- Подтверждение почты (ADR-0012). Уже существующие аккаунты считаем подтверждёнными:
-- их создавали до появления проверки (в том числе модераторы через CLI).
ALTER TABLE users ADD COLUMN email_verified_at timestamptz;
UPDATE users SET email_verified_at = created_at;

CREATE TABLE email_verifications (
    token_hash text PRIMARY KEY,
    user_id    uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL
);
CREATE INDEX email_verifications_user_idx ON email_verifications (user_id, created_at DESC);
