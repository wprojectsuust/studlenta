import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { feedItem } from "@/test/fixtures";
import { EventStrip } from "./EventStrip";

const NOW = new Date("2026-10-23T07:00:00Z");
const items = [1, 2, 3, 4].map((n) => feedItem({ id: `e${n}`, title: `Событие ${n}` }));

describe("EventStrip", () => {
  it("is a labelled list of event links", () => {
    render(<EventStrip title="Ближайшие" items={items} now={NOW} />);
    const region = screen.getByRole("region", { name: "Ближайшие" });
    expect(region).toBeInTheDocument();
    const links = screen.getAllByRole("link");
    expect(links.map((l) => l.getAttribute("href"))).toEqual(["/events/e1", "/events/e2", "/events/e3", "/events/e4"]);
    expect(links[0]).toHaveAccessibleName(/Событие 1/);
  });

  it("scrolls with the arrow buttons", async () => {
    render(<EventStrip title="Ближайшие" items={items} now={NOW} />);
    const list = screen.getByRole("list");
    list.scrollBy = vi.fn();
    await userEvent.click(screen.getByRole("button", { name: "Прокрутить вперёд" }));
    await userEvent.click(screen.getByRole("button", { name: "Прокрутить назад" }));
    const calls = vi.mocked(list.scrollBy).mock.calls.map((c) => (c[0] as ScrollToOptions).left ?? 0);
    expect(calls[0]).toBeGreaterThanOrEqual(0);
    expect(calls[1]).toBeLessThanOrEqual(0);
  });

  it("shows a reason under the title when given (recommendations)", () => {
    render(<EventStrip title="Для вас" items={items.slice(0, 1)} reasons={{ e1: "Похоже на «Хакатон»" }} now={NOW} />);
    expect(screen.getByText("Похоже на «Хакатон»")).toBeInTheDocument();
  });

  it("renders nothing without items", () => {
    const { container } = render(<EventStrip title="Ближайшие" items={[]} now={NOW} />);
    expect(container).toBeEmptyDOMElement();
  });
});
