"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ApiError, endpoints } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type State = { kind: "checking" } | { kind: "done" } | { kind: "failed"; message: string };

export function VerifyEmailView() {
  const token = useSearchParams().get("token") ?? "";
  const { reloadProfile, status } = useAuth();
  const [state, setState] = useState<State>({ kind: "checking" });
  const sent = useRef(false);

  useEffect(() => {
    if (sent.current) return; // ссылка одноразовая по смыслу — не шлём дважды в StrictMode
    sent.current = true;
    endpoints
      .verifyEmail(token)
      .then(() => setState({ kind: "done" }))
      .catch((e: unknown) =>
        setState({ kind: "failed", message: e instanceof ApiError ? (e.fields.token ?? e.message) : "Не удалось подтвердить почту" }),
      );
  }, [token]);

  useEffect(() => {
    if (state.kind === "done" && status === "authenticated") void reloadProfile();
  }, [state.kind, status, reloadProfile]);

  return (
    <div className="card" style={{ padding: 28, display: "flex", flexDirection: "column", gap: 14 }} aria-live="polite">
      <h1 className="page-title">Подтверждение почты</h1>
      {state.kind === "checking" && <p>Проверяем ссылку…</p>}
      {state.kind === "done" && (
        <>
          <p>Готово, почта подтверждена. Теперь можно отправлять события на модерацию.</p>
          <Link href="/my/new" className="btn btn-primary" style={{ alignSelf: "flex-start" }}>Предложить событие</Link>
        </>
      )}
      {state.kind === "failed" && (
        <>
          <p role="alert" style={{ color: "var(--color-danger)" }}>{state.message}</p>
          <Link href={status === "authenticated" ? "/my" : "/login"} className="btn btn-secondary" style={{ alignSelf: "flex-start" }}>
            {status === "authenticated" ? "В профиль" : "Войти"}
          </Link>
        </>
      )}
    </div>
  );
}
