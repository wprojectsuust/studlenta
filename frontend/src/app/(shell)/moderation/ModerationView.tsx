"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Cover } from "@/components/Cover";
import { CardSkeleton, EmptyState, ErrorBanner } from "@/components/Feedback";
import { ModerationPanel } from "@/components/ModerationPanel";
import { TagPill } from "@/components/TagPill";
import { ApiError, canModerate, endpoints, type EventStatus } from "@/lib/api";
import { formatWhen } from "@/lib/format";
import { useHistory, useQueue } from "@/lib/queries";
import { useRequireAuth } from "@/lib/useRequireAuth";

const TABS: { id: EventStatus; label: string }[] = [
  { id: "pending", label: "На проверке" },
  { id: "changes_requested", label: "На доработке" },
  { id: "published", label: "Одобренные" },
  { id: "rejected", label: "Отклонённые" },
];
const NEUTRAL = { id: 0, slug: "", name: "", color: "#4B5563" };

export function ModerationView() {
  const auth = useRequireAuth();
  const allowed = canModerate(auth.user?.role);
  const client = useQueryClient();
  const [tab, setTab] = useState<EventStatus>("pending");
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const queue = useQueue(tab, allowed);
  const current = queue.data?.find((e) => e.id === selected) ?? queue.data?.[0] ?? null;
  const history = useHistory(current?.id ?? null);

  async function decide(fn: () => Promise<void>, done: string) {
    if (!current) return;
    setBusy(true);
    setError(null);
    try {
      await fn();
      setToast(`${done}: «${current.title}»`);
      setSelected(null);
    } catch (e) {
      setError(e instanceof ApiError && e.status === 409 ? "Заявку уже обработал другой модератор — обновили очередь." : e instanceof Error ? e.message : "Не получилось");
    } finally {
      setBusy(false);
      await client.invalidateQueries({ queryKey: ["moderation"] });
      await client.invalidateQueries({ queryKey: ["feed"] });
    }
  }

  if (auth.status !== "authenticated") return <CardSkeleton />;
  if (!allowed) return <EmptyState title="Раздел для модераторов">Модераторов назначает администратор.</EmptyState>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
        <h1 className="page-title">Модерация</h1>
        {toast && <p role="status" style={{ padding: "8px 14px", borderRadius: 10, background: "#111827", color: "#FFFFFF", fontSize: 14 }}>{toast}</p>}
      </div>
      <div role="group" aria-label="Статус заявок" style={{ display: "flex", flexWrap: "wrap", gap: 4, borderBottom: "1px solid var(--color-line)" }}>
        {TABS.map((t) => (
          <button key={t.id} type="button" aria-pressed={tab === t.id} onClick={() => { setTab(t.id); setSelected(null); }}
            style={{ minHeight: 44, padding: "0 14px", border: 0, marginBottom: -1, background: "transparent", fontWeight: 600, fontSize: 14,
              borderBottom: `3px solid ${tab === t.id ? "var(--color-accent)" : "transparent"}`, color: tab === t.id ? "var(--color-accent-text)" : "var(--color-muted)" }}>
            {t.label}{tab === t.id && queue.data ? ` (${queue.data.length})` : ""}
          </button>
        ))}
      </div>
      {error && <ErrorBanner message={error} />}
      {queue.isPending && <CardSkeleton />}
      {queue.data?.length === 0 && <EmptyState title="Здесь пусто">{tab === "pending" ? "Новых заявок нет." : "Пока ничего."}</EmptyState>}
      {queue.data && current && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 20, alignItems: "flex-start" }}>
          <ul aria-label="Заявки" style={{ flex: "1 1 360px", minWidth: 0, margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 10 }}>
            {queue.data.map((e) => {
              const on = e.id === current.id;
              return (
                <li key={e.id}>
                  <button type="button" aria-pressed={on} onClick={() => setSelected(e.id)} className="card"
                    style={{ width: "100%", display: "flex", gap: 14, padding: 12, textAlign: "left", borderWidth: 2, borderColor: on ? "var(--color-accent)" : "var(--color-line)" }}>
                    <Cover src={e.cover_url} category={e.category ?? NEUTRAL} style={{ width: 88, height: 64, borderRadius: 8, flex: "none" }} />
                    <span style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: 4 }}>
                      <strong style={{ fontSize: 15 }}>{e.title}</strong>
                      <span style={{ fontSize: 13, color: "var(--color-muted)" }}>{e.author_name}{e.submitted_at ? ` · ${formatWhen(e.submitted_at)}` : ""}</span>
                      <span style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                        {e.category && <TagPill category={e.category} />}
                        {e.is_resubmission && <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-warning-ink)" }}>Исправлено автором</span>}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          <div style={{ flex: "999 1 560px", minWidth: 0 }}>
            <ModerationPanel key={current.id} event={current} history={history.data ?? []} busy={busy}
              onApprove={() => void decide(() => endpoints.approve(current.id), "Опубликовано")}
              onRequestChanges={(note) => void decide(() => endpoints.requestChanges(current.id, note), "Возвращено на доработку")}
              onReject={(note) => void decide(() => endpoints.reject(current.id, note), "Отклонено")} />
          </div>
        </div>
      )}
    </div>
  );
}
