import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, endpoints } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { readGuestFavorites, toggleGuestFavorite } from "@/lib/guestFavorites";
import { profile } from "@/test/fixtures";
import { wrapper } from "@/test/render";

vi.mock("@/lib/api", async (orig) => {
  const mod = await orig<typeof import("@/lib/api")>();
  return { ...mod, api: { ...mod.api, refresh: vi.fn(), setAccessToken: vi.fn(), getAccessToken: vi.fn() } };
});

describe("useAuth", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("is a guest when there is no session cookie", async () => {
    vi.mocked(api.refresh).mockResolvedValue(false);
    const { result } = renderHook(() => useAuth(), { wrapper: wrapper() });
    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current.status).toBe("guest"));
    expect(result.current.user).toBeNull();
  });

  it("restores the session on load", async () => {
    vi.mocked(api.refresh).mockResolvedValue(true);
    vi.spyOn(endpoints, "me").mockResolvedValue(profile);
    const { result } = renderHook(() => useAuth(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.status).toBe("authenticated"));
    expect(result.current.user?.full_name).toBe("Анна Смирнова");
  });

  it("moves guest favorites to the account after login", async () => {
    vi.mocked(api.refresh).mockResolvedValue(false);
    toggleGuestFavorite("e1");
    vi.spyOn(endpoints, "login").mockResolvedValue({ access_token: "t", token_type: "bearer", expires_in: 900 });
    vi.spyOn(endpoints, "me").mockResolvedValue(profile);
    const sync = vi.spyOn(endpoints, "syncFavorites").mockResolvedValue({ added: 1 });

    const { result } = renderHook(() => useAuth(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.status).toBe("guest"));
    await act(() => result.current.login("anna@uust.ru", "password1"));

    expect(api.setAccessToken).toHaveBeenCalledWith("t");
    expect(sync).toHaveBeenCalledWith(["e1"]);
    expect(readGuestFavorites()).toEqual([]);
    expect(result.current.status).toBe("authenticated");
  });

  it("logs out locally even if the server is unreachable", async () => {
    vi.mocked(api.refresh).mockResolvedValue(true);
    vi.spyOn(endpoints, "me").mockResolvedValue(profile);
    vi.spyOn(endpoints, "logout").mockRejectedValue(new Error("offline"));
    const { result } = renderHook(() => useAuth(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.status).toBe("authenticated"));
    await act(() => result.current.logout());
    expect(result.current.status).toBe("guest");
    expect(api.setAccessToken).toHaveBeenLastCalledWith(null);
  });
});
