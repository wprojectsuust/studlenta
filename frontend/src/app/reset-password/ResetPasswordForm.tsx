"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ApiError, endpoints } from "@/lib/api";

export function ResetPasswordForm() {
  const token = useSearchParams().get("token") ?? "";
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState(false);
  const [errors, setErrors] = useState<{ password?: string; token?: string; other?: string }>({});

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    try {
      await endpoints.resetPassword(token, String(new FormData(e.currentTarget).get("password") ?? ""));
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setErrors(err.fields);
      else setErrors({ other: err instanceof Error ? err.message : "Не удалось сохранить" });
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="card" role="status" style={{ padding: 28, display: "flex", flexDirection: "column", gap: 14 }}>
        <h1 className="page-title">Пароль изменён</h1>
        <p>Войдите с новым паролем. Все остальные сессии мы на всякий случай завершили.</p>
        <Link href="/login" className="btn btn-primary" style={{ alignSelf: "flex-start" }}>Войти</Link>
      </div>
    );
  }

  return (
    <form onSubmit={submit} noValidate className="card" style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16 }}>
      <h1 className="page-title">Новый пароль</h1>
      {(errors.token || errors.other) && (
        <div role="alert" style={{ padding: "12px 14px", borderRadius: 10, background: "var(--color-danger-bg)", color: "var(--color-danger-ink)" }}>
          {errors.token ?? errors.other} {errors.token && <Link href="/forgot-password">Запросить снова</Link>}
        </div>
      )}
      <div className="field">
        <label htmlFor="password">Новый пароль</label>
        <div style={{ display: "flex" }}>
          <input id="password" name="password" type={show ? "text" : "password"} className="input" autoComplete="new-password"
            aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? "password-error" : "password-hint"}
            style={{ flex: 1, borderTopRightRadius: 0, borderBottomRightRadius: 0 }} />
          <button type="button" className="btn btn-secondary" aria-pressed={show} onClick={() => setShow((v) => !v)}
            style={{ borderTopLeftRadius: 0, borderBottomLeftRadius: 0, borderLeft: 0 }}>{show ? "Скрыть" : "Показать"}</button>
        </div>
        {errors.password ? <span id="password-error" className="error">{errors.password}</span> : <span id="password-hint" className="hint">Минимум 8 символов</span>}
      </div>
      <button type="submit" className="btn btn-primary" disabled={busy || !token}>Сохранить пароль</button>
    </form>
  );
}
