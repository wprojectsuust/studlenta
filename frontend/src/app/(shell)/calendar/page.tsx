import type { Metadata } from "next";
import { Suspense } from "react";
import { CardSkeleton } from "@/components/Feedback";
import { CalendarView } from "./CalendarView";

export const metadata: Metadata = { title: "Календарь" };

export default function CalendarPage() {
  return (
    <Suspense fallback={<CardSkeleton />}>
      <CalendarView />
    </Suspense>
  );
}
