import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Suspense } from "react";
import { PlainHeader } from "@/components/PlainHeader";
import { getPublishedEvent } from "@/lib/server";
import { EventView } from "./EventView";

export async function generateMetadata({ params }: PageProps<"/events/[id]">): Promise<Metadata> {
  const { id } = await params;
  const event = await getPublishedEvent(id);
  if (!event) return { title: "Событие недоступно" };
  return {
    title: event.title,
    description: event.summary,
    openGraph: {
      type: "article",
      title: event.title,
      description: event.summary,
      images: event.cover_url ? [{ url: event.cover_url }] : undefined,
    },
  };
}

// Метаданные зависят от params — помечаем страницу как динамическую (см. migrating-to-cache-components).
async function DynamicMarker() {
  await connection();
  return null;
}

async function EventContent({ params }: { params: PageProps<"/events/[id]">["params"] }) {
  const { id } = await params;
  const event = await getPublishedEvent(id);
  if (!event) notFound();
  return <EventView initial={event} />;
}

export default function EventPage({ params }: PageProps<"/events/[id]">) {
  return (
    <>
      <PlainHeader href="/" label="Назад к ленте" />
      <main id="main" style={{ maxWidth: 1240, margin: "0 auto", padding: "28px 24px 56px" }}>
        <Suspense fallback={<p>Загружаем событие…</p>}>
          <EventContent params={params} />
        </Suspense>
        <Suspense>
          <DynamicMarker />
        </Suspense>
      </main>
    </>
  );
}
