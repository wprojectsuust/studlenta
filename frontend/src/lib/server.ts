// Только для серверных компонентов: публичные данные события с кешем на минуты.
import { cacheLife } from "next/cache";
import type { EventDetails } from "@/lib/api/types";

const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function getPublishedEvent(id: string): Promise<EventDetails | null> {
  "use cache";
  cacheLife("minutes");
  if (!UUID.test(id)) return null;
  const res = await fetch(`${API}/api/v1/events/${id}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API ответил ${res.status}`);
  return (await res.json()) as EventDetails;
}
