import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { InterestReport } from "@/lib/api";
import { Report } from "./AnalyticsView";

const music = { id: 1, slug: "concerts", name: "Концерты", color: "#7C3AED" };
const report: InterestReport = {
  scope: "all",
  days: 7,
  totals: { views: 1284, viewers: 300, likes: 12, favorites: 9 },
  daily: [
    { day: "2026-10-22", views: 4, viewers: 3 },
    { day: "2026-10-23", views: 10, viewers: 6 },
  ],
  categories: [{ category: music, events: 2, views: 14, likes: 3, favorites: 2 }],
  top: [{ id: "e1", title: "Джазовый вечер", category: music, starts_at: "2026-10-25T13:00:00Z", views: 14, viewers: 10, likes: 3, favorites: 4 }],
};

describe("analytics report", () => {
  it("shows compact totals, the peak day and a table for screen readers", () => {
    render(<Report data={report} />);
    const totals = screen.getByRole("list", { name: "Итоги за период" });
    expect(within(totals).getByText("1,3 тыс.")).toBeInTheDocument();
    expect(screen.getByText("Пик — 23 окт.: 10 просмотров")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /максимум 10/ })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: "23 окт. 10 6" })).toBeInTheDocument();
  });

  it("links top events and computes favourite conversion", () => {
    render(<Report data={report} />);
    expect(screen.getByRole("link", { name: "Джазовый вечер" })).toHaveAttribute("href", "/events/e1");
    expect(screen.getByRole("cell", { name: "40%" })).toBeInTheDocument();
  });

  it("explains an empty period instead of drawing zero charts", () => {
    render(<Report data={{ ...report, totals: { views: 0, viewers: 0, likes: 0, favorites: 0 } }} />);
    expect(screen.getByText("Пока тихо")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
