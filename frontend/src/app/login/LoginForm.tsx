"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { CapIcon } from "@/components/icons";
import { ApiError, type FieldErrors } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** Только внутренние пути: защита от open redirect через ?next=https://… */
function safeNext(value: string | null) {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/";
}

export function LoginForm() {
  const params = useSearchParams();
  const router = useRouter();
  const auth = useAuth();
  const [mode, setMode] = useState<"login" | "register">(params.get("mode") === "register" ? "register" : "login");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState(false);
  const next = safeNext(params.get("next"));

  useEffect(() => {
    if (auth.status === "authenticated") router.replace(next);
  }, [auth.status, next, router]);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");
    setBusy(true);
    setErrors({});
    setMessage(null);
    try {
      if (mode === "login") await auth.login(email, password);
      else await auth.register(email, password, String(form.get("full_name") ?? ""));
      router.replace(next);
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setErrors(err.fields);
      else setMessage(err instanceof Error ? err.message : "Не удалось войти");
    } finally {
      setBusy(false);
    }
  }

  const field = (name: string, label: string, input: React.ReactNode, hint?: string) => (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      {input}
      {hint && !errors[name] && <span id={`${name}-hint`} className="hint">{hint}</span>}
      {errors[name] && <span id={`${name}-error`} className="error">{errors[name]}</span>}
    </div>
  );
  const describedBy = (name: string, hint?: boolean) => (errors[name] ? `${name}-error` : hint ? `${name}-hint` : undefined);

  return (
    <div className="login-page">
      <section className="login-brand" aria-hidden="true">
        <span style={{ display: "flex", alignItems: "center", gap: 12 }}><CapIcon size={34} /><strong style={{ fontSize: 18 }}>УУНиТ · Студенческие события</strong></span>
        <p style={{ fontSize: 30, lineHeight: 1.2, fontWeight: 700, maxWidth: 440 }}>Всё, что происходит в университете, — в одной ленте</p>
      </section>
      <main id="main" className="login-main">
        <form onSubmit={submit} noValidate style={{ width: "100%", maxWidth: 420, display: "flex", flexDirection: "column", gap: 18 }}>
          <div role="group" aria-label="Режим" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", padding: 4, gap: 4, borderRadius: 12, background: "var(--color-chip)" }}>
            {(["login", "register"] as const).map((m) => (
              <button key={m} type="button" aria-pressed={mode === m} onClick={() => { setMode(m); setErrors({}); setMessage(null); }}
                className="btn" style={{ background: mode === m ? "var(--color-surface)" : "transparent" }}>
                {m === "login" ? "Вход" : "Регистрация"}
              </button>
            ))}
          </div>
          <h1 className="page-title">{mode === "login" ? "Вход" : "Создать аккаунт"}</h1>
          {message && <div role="alert" style={{ padding: "12px 14px", borderRadius: 10, background: "var(--color-danger-bg)", color: "var(--color-danger-ink)" }}>{message}</div>}
          {mode === "register" && field("full_name", "Имя и фамилия",
            <input id="full_name" name="full_name" className="input" autoComplete="name" aria-invalid={Boolean(errors.full_name)} aria-describedby={describedBy("full_name")} />)}
          {field("email", "Почта",
            <input id="email" name="email" type="email" className="input" autoComplete="email" required aria-invalid={Boolean(errors.email)} aria-describedby={describedBy("email")} />)}
          {field("password", "Пароль",
            <div style={{ display: "flex" }}>
              <input id="password" name="password" type={show ? "text" : "password"} className="input" style={{ flex: 1, borderTopRightRadius: 0, borderBottomRightRadius: 0 }}
                autoComplete={mode === "login" ? "current-password" : "new-password"} required aria-invalid={Boolean(errors.password)}
                aria-describedby={describedBy("password", mode === "register")} />
              <button type="button" className="btn btn-secondary" aria-pressed={show} onClick={() => setShow((v) => !v)}
                style={{ borderTopLeftRadius: 0, borderBottomLeftRadius: 0, borderLeft: 0 }}>
                {show ? "Скрыть" : "Показать"}
              </button>
            </div>, mode === "register" ? "Минимум 8 символов" : undefined)}
          <button type="submit" className="btn btn-primary" disabled={busy} aria-busy={busy} style={{ minHeight: 48 }}>
            {mode === "login" ? "Войти" : "Зарегистрироваться"}
          </button>
          <p style={{ textAlign: "center", color: "var(--color-muted)", fontSize: 14 }}>Можно и без входа — <Link href="/">смотреть ленту</Link></p>
        </form>
      </main>
    </div>
  );
}
