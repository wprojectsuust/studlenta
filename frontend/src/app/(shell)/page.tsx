import { Suspense } from "react";
import { CardSkeleton } from "@/components/Feedback";
import { FeedView } from "./FeedView";

export default function FeedPage() {
  return (
    <Suspense fallback={<CardSkeleton />}>
      <FeedView />
    </Suspense>
  );
}
