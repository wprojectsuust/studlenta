import type { Metadata } from "next";
import { ModerationView } from "./ModerationView";

export const metadata: Metadata = { title: "Модерация" };

export default function ModerationPage() {
  return <ModerationView />;
}
