import type { Metadata } from "next";
import { Suspense } from "react";
import { EventEditor } from "@/components/EventEditor";

export const metadata: Metadata = { title: "Редактирование события" };

async function Editor({ params }: { params: PageProps<"/my/[id]/edit">["params"] }) {
  const { id } = await params;
  return <EventEditor eventId={id} />;
}

export default function EditEventPage({ params }: PageProps<"/my/[id]/edit">) {
  return (
    <Suspense>
      <Editor params={params} />
    </Suspense>
  );
}
