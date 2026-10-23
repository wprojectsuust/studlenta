"use client";

import { useState, type FormEvent } from "react";
import { endpoints } from "@/lib/api";

export function ForgotPasswordForm() {
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await endpoints.requestPasswordReset(String(new FormData(e.currentTarget).get("email") ?? ""));
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отправить");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="card" style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16 }}>
      <h1 className="page-title">Восстановление пароля</h1>
      <p style={{ color: "var(--color-muted)" }}>Укажите почту, с которой регистрировались, — пришлём ссылку для нового пароля.</p>
      <div className="field">
        <label htmlFor="email">Почта</label>
        <input id="email" name="email" type="email" className="input" autoComplete="email" required />
      </div>
      {error && <p role="alert" style={{ color: "var(--color-danger)" }}>{error}</p>}
      <button type="submit" className="btn btn-primary" disabled={busy}>Прислать ссылку</button>
      <p role="status" style={{ color: "var(--color-muted)", fontSize: 14 }}>
        {sent ? "Если такой аккаунт есть, письмо уже в пути. Ссылка действует час. Загляните и в «Спам»." : ""}
      </p>
    </form>
  );
}
