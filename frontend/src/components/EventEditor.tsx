"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useRef } from "react";
import { endpoints, type AuthoredEvent, type EventInput } from "@/lib/api";
import { useCategories } from "@/lib/queries";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { EventForm } from "./EventForm";
import { CardSkeleton, EmptyState } from "./Feedback";
import { PlainHeader } from "./PlainHeader";
import { VerifyNotice } from "./Shell";

/** Создание (eventId = null) и правка события. Первое автосохранение создаёт черновик. */
export function EventEditor({ eventId }: { eventId: string | null }) {
  const auth = useRequireAuth();
  const router = useRouter();
  const client = useQueryClient();
  const categories = useCategories();
  const idRef = useRef<string | null>(eventId);
  const existing = useQuery({
    queryKey: ["me", "event", eventId],
    queryFn: () => endpoints.myEvent(eventId ?? ""),
    enabled: eventId !== null && auth.status === "authenticated",
  });

  const save = useCallback(async (input: EventInput) => {
    if (idRef.current) await endpoints.updateEvent(idRef.current, input);
    else {
      idRef.current = (await endpoints.createEvent(input)).id;
      window.history.replaceState(null, "", `${window.location.pathname.replace(/\/new$/, "")}/${idRef.current}/edit`);
    }
  }, []);

  const submit = useCallback(async (input: EventInput) => {
    await save(input);
    await endpoints.submit(idRef.current ?? "");
    await client.invalidateQueries({ queryKey: ["me"] });
    router.push("/my");
  }, [client, router, save]);

  const editable = (e?: AuthoredEvent) => !e || e.status === "draft" || e.status === "changes_requested";
  const title = eventId ? "Редактирование события" : "Новое событие";

  return (
    <>
      <PlainHeader href="/my" label="Мои публикации" />
      <VerifyNotice />
      <main id="main" style={{ maxWidth: 960, margin: "0 auto", padding: "28px 24px 56px", display: "flex", flexDirection: "column", gap: 20 }}>
        <h1 className="page-title">{title}</h1>
        <p style={{ color: "var(--color-muted)" }}>Событие появится в ленте после проверки модератором.</p>
        {existing.data?.status === "changes_requested" && existing.data.moderator_note && (
          <div role="note" style={{ padding: "12px 14px", borderRadius: 10, background: "var(--color-warning-bg)", color: "var(--color-warning-ink)" }}>
            <strong>Модератор просит поправить:</strong> {existing.data.moderator_note}
          </div>
        )}
        {auth.status !== "authenticated" || !categories.data || (eventId && existing.isPending) ? (
          <CardSkeleton />
        ) : !editable(existing.data) ? (
          <EmptyState title="Это событие сейчас нельзя менять">Отзовите заявку с модерации в «Моих публикациях», чтобы отредактировать.</EmptyState>
        ) : (
          <EventForm initial={existing.data} categories={categories.data} onSave={save} onSubmit={submit}
            onUpload={async (file) => (await endpoints.uploadCover(file)).url} />
        )}
      </main>
    </>
  );
}
