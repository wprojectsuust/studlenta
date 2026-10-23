import type { Metadata } from "next";
import { EventEditor } from "@/components/EventEditor";

export const metadata: Metadata = { title: "Новое событие" };

export default function NewEventPage() {
  return <EventEditor eventId={null} />;
}
