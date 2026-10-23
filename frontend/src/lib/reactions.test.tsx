import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApiError, api, endpoints, type Page } from "@/lib/api";
import { useReactions } from "@/lib/queries";
import { readGuestFavorites } from "@/lib/guestFavorites";
import { feedItem, profile } from "@/test/fixtures";
import { makeClient, wrapper } from "@/test/render";

vi.mock("@/lib/api", async (orig) => {
  const mod = await orig<typeof import("@/lib/api")>();
  return { ...mod, api: { ...mod.api, refresh: vi.fn(), setAccessToken: vi.fn() } };
});

function seedFeed(client: ReturnType<typeof makeClient>) {
  const page: Page = { items: [feedItem()], next_cursor: null };
  client.setQueryData(["feed", { period: "all" }], { pages: [page], pageParams: [null] });
  return () => (client.getQueryData(["feed", { period: "all" }]) as { pages: Page[] }).pages[0]!.items[0]!;
}

describe("useReactions", () => {
  it("guest favorites go to localStorage and update the cache", async () => {
    vi.mocked(api.refresh).mockResolvedValue(false);
    const client = makeClient();
    const item = seedFeed(client);
    const { result } = renderHook(() => useReactions(), { wrapper: wrapper(client) });
    await waitFor(() => expect(result.current.isGuest).toBe(true));

    await act(() => result.current.toggleFavorite(feedItem()));
    expect(readGuestFavorites()).toEqual(["e1"]);
    expect(item().favorited).toBe(true);
  });

  it("likes optimistically and rolls back on error", async () => {
    vi.mocked(api.refresh).mockResolvedValue(true);
    vi.spyOn(endpoints, "me").mockResolvedValue(profile);
    let fail = false;
    vi.spyOn(endpoints, "like").mockImplementation(async () => {
      if (fail) throw new ApiError(500, "x", "Сбой");
    });
    const client = makeClient();
    const item = seedFeed(client);
    const { result } = renderHook(() => useReactions(), { wrapper: wrapper(client) });
    await waitFor(() => expect(result.current.isGuest).toBe(false));

    await act(() => result.current.toggleLike(feedItem()));
    expect(item()).toMatchObject({ liked: true, likes_count: 43 });

    fail = true;
    await act(() => result.current.toggleLike(item()).catch(() => undefined));
    expect(item()).toMatchObject({ liked: true, likes_count: 43 });
    expect(result.current.error).toBe("Не удалось сохранить, попробуйте ещё раз");
  });

  it("asks a guest to log in for likes", async () => {
    vi.mocked(api.refresh).mockResolvedValue(false);
    const { result } = renderHook(() => useReactions(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isGuest).toBe(true));
    await act(() => result.current.toggleLike(feedItem()));
    expect(result.current.needsLogin).toBe(true);
  });
});
