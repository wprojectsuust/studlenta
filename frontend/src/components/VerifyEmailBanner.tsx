"use client";

import { useState } from "react";

type Props = { email: string; onResend: () => Promise<{ sent: boolean }> };

/** Пока почта не подтверждена, события нельзя отправить на модерацию (ADR-0012). */
export function VerifyEmailBanner({ email, onResend }: Props) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function resend() {
    setBusy(true);
    try {
      const { sent } = await onResend();
      setMessage(sent ? "Письмо отправлено. Проверьте почту и папку «Спам»." : "Почта уже подтверждена — обновите страницу.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Не удалось отправить письмо");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Подтвердите почту" style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px 16px", padding: "12px 32px",
      background: "var(--color-warning-bg)", color: "var(--color-warning-ink)", borderBottom: "1px solid var(--color-line)", fontSize: 14 }}>
      <span style={{ flex: "1 1 320px" }}>
        <strong>Подтвердите почту.</strong> Мы отправили ссылку на {email} — без этого события нельзя отправить на модерацию.
        Письма может не быть во «Входящих»: загляните в «Спам».
      </span>
      <button type="button" className="btn btn-secondary" onClick={() => void resend()} disabled={busy}>Отправить ещё раз</button>
      <span role="status" style={{ flexBasis: "100%" }}>{message}</span>
    </section>
  );
}
