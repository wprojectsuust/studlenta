import type { Metadata } from "next";
import { MyEventsView } from "./MyEventsView";

export const metadata: Metadata = { title: "Мои публикации" };

export default function MyPage() {
  return <MyEventsView />;
}
