import type { Metadata } from "next";
import { AnalyticsView } from "./AnalyticsView";

export const metadata: Metadata = { title: "Аналитика интересов" };

export default function AnalyticsPage() {
  return <AnalyticsView />;
}
