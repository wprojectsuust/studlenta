import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { feedItem } from "@/test/fixtures";
import { EventCard } from "./EventCard";

const NOW = new Date("2026-10-23T07:00:00Z");

describe("EventCard", () => {
  it("shows the essentials with a single link to the event", () => {
    render(<EventCard item={feedItem()} now={NOW} onLike={vi.fn()} onFavorite={vi.fn()} />);
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAccessibleName("Вечер студенческой музыки");
    expect(links[0]).toHaveAttribute("href", "/events/e1");
    expect(screen.getByText("Концерты")).toBeInTheDocument();
    expect(screen.getByText("Сегодня, 18:00")).toBeInTheDocument();
    expect(screen.getByText("Актовый зал УУНиТ")).toBeInTheDocument();
    expect(screen.getByText("Сегодня", { selector: "[data-badge]" })).toBeInTheDocument();
  });

  it("exposes like and favorite as toggle buttons", async () => {
    const onLike = vi.fn();
    const onFavorite = vi.fn();
    render(<EventCard item={feedItem({ liked: true, likes_count: 43 })} now={NOW} onLike={onLike} onFavorite={onFavorite} />);
    const like = screen.getByRole("button", { name: "Нравится, 43" });
    expect(like).toHaveAttribute("aria-pressed", "true");
    const fav = screen.getByRole("button", { name: "Добавить в избранное" });
    expect(fav).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(like);
    await userEvent.click(fav);
    expect(onLike).toHaveBeenCalledOnce();
    expect(onFavorite).toHaveBeenCalledOnce();
  });

  it("falls back to a category-coloured cover", () => {
    const { container } = render(<EventCard item={feedItem({ cover_url: null })} now={NOW} onLike={vi.fn()} onFavorite={vi.fn()} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("[data-cover-fallback]")).toHaveStyle({ backgroundColor: "#7C3AED" });
  });
});
