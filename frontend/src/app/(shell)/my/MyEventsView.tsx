"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Cover } from "@/components/Cover";
import { CardSkeleton, EmptyState, ErrorBanner } from "@/components/Feedback";
import { PlusIcon } from "@/components/icons";
import { SkinPicker } from "@/components/SkinPicker";
import { StatusBadge, statusLabel } from "@/components/StatusBadge";
import { canModerate, endpoints, type EventStatus, type MyEvent } from "@/lib/api";
import { formatWhen } from "@/lib/format";
import { useMyEvents } from "@/lib/queries";
import { useRequireAuth } from "@/lib/useRequireAuth";

const FILTERS: (EventStatus | "all")[] = ["all", "draft", "pending", "changes_requested", "published", "rejected", "archived"];
const NEUTRAL = { id: 0, slug: "", name: "", color: "#4B5563" };

export function MyEventsView() {
  const auth = useRequireAuth();
  const client = useQueryClient();
  const router = useRouter();
  const [filter, setFilter] = useState<EventStatus | "all">("all");
  const all = useMyEvents();
  const [message, setMessage] = useState<string | null>(null);
  const items = (all.data ?? []).filter((e) => filter === "all" || e.status === filter);

  async function act(fn: () => Promise<void>, done: string) {
    try {
      await fn();
      setMessage(done);
      await client.invalidateQueries({ queryKey: ["me"] });
      await client.invalidateQueries({ queryKey: ["feed"] });
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Не получилось");
    }
  }

  function actions(e: MyEvent) {
    switch (e.status) {
      case "draft":
        return (
          <>
            <Link className="btn btn-primary" href={`/my/${e.id}/edit`}>Продолжить</Link>
            <button type="button" className="btn btn-danger" onClick={() => void act(() => endpoints.deleteEvent(e.id), "Черновик удалён")}>Удалить</button>
          </>
        );
      case "changes_requested":
        return <Link className="btn btn-primary" href={`/my/${e.id}/edit`}>Исправить</Link>;
      case "pending":
        return <button type="button" className="btn btn-secondary" onClick={() => void act(() => endpoints.withdraw(e.id), "Заявка отозвана — теперь это черновик")}>Отозвать</button>;
      case "published":
        return (
          <>
            <Link className="btn btn-secondary" href={`/events/${e.id}`}>Открыть</Link>
            <button type="button" className="btn btn-ghost" onClick={() => void act(() => endpoints.archive(e.id), "Событие снято с публикации")}>Снять с публикации</button>
          </>
        );
      default:
        return null;
    }
  }

  // После выхода — в ленту, а не на форму входа (её бы показала защита закрытой страницы).
  async function logout() {
    router.replace("/");
    await auth.logout();
  }

  if (auth.status !== "authenticated") return <CardSkeleton />;

  return (
    <div style={{ maxWidth: 1040, display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
        <h1 className="page-title">Мои публикации</h1>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {canModerate(auth.user?.role) && <Link href="/moderation" className="btn btn-secondary">Модерация</Link>}
          <Link href="/analytics" className="btn btn-secondary">Аналитика</Link>
          <Link href="/my/new" className="btn btn-primary"><PlusIcon size={18} />Новое событие</Link>
          <button type="button" className="btn btn-ghost" onClick={() => void logout()}>Выйти</button>
        </div>
      </div>
      <p style={{ color: "var(--color-muted)" }}>{auth.user?.full_name} · {auth.user?.email}</p>
      {/* На телефоне сайдбара нет — скин выбирается здесь */}
      <div className="show-mobile" style={{ maxWidth: 360 }}><SkinPicker tone="page" /></div>

      <div role="group" aria-label="Статус" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {FILTERS.map((f) => {
          const count = f === "all" ? all.data?.length : all.data?.filter((e) => e.status === f).length;
          return (
            <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)} className="btn"
              style={{ fontSize: 14, background: filter === f ? "var(--color-ink)" : "var(--color-surface)", color: filter === f ? "var(--color-bg)" : "var(--color-ink)", borderColor: "var(--color-line)" }}>
              {f === "all" ? "Все" : statusLabel(f)} {count ?? ""}
            </button>
          );
        })}
      </div>

      {message && <p role="status" style={{ padding: "10px 14px", borderRadius: 10, background: "var(--color-info-bg)", color: "var(--color-info-ink)" }}>{message}</p>}
      {all.isError && <ErrorBanner message="Не удалось загрузить публикации." onRetry={() => void all.refetch()} />}
      {all.isPending && <CardSkeleton />}
      {all.data && items.length === 0 && (
        <EmptyState title="Здесь пока пусто">Расскажите о событии — после проверки оно появится в ленте. <Link href="/my/new">Предложить событие</Link></EmptyState>
      )}
      {items.map((e) => (
        <article key={e.id} className="card" style={{ display: "flex", flexWrap: "wrap", gap: "16px 20px", padding: 14 }} aria-labelledby={`my-${e.id}`}>
          <Cover src={e.cover_url} category={NEUTRAL} sizes="132px" style={{ width: 132, height: 92, borderRadius: 10, flex: "none" }} />
          <div style={{ flex: "1 1 320px", minWidth: 0, display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", fontSize: 13, color: "var(--color-muted)" }}>
              <StatusBadge status={e.status} />
              {e.starts_at && <span>{formatWhen(e.starts_at)}</span>}
              {e.status === "published" && <span>♥ {e.likes_count} · в избранном у {e.favorites_count}</span>}
            </div>
            <h2 id={`my-${e.id}`} style={{ fontSize: 17, fontWeight: 600 }}>{e.title}</h2>
            {e.moderator_note && (e.status === "changes_requested" || e.status === "rejected") && (
              <p style={{ fontSize: 14 }}><strong>Модератор:</strong> {e.moderator_note}</p>
            )}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>{actions(e)}</div>
        </article>
      ))}
    </div>
  );
}
