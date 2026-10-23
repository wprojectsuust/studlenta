import { describe, expect, it } from "vitest";
import { clearGuestFavorites, readGuestFavorites, toggleGuestFavorite } from "./guestFavorites";

describe("guest favorites", () => {
  it("toggles ids in localStorage", () => {
    expect(readGuestFavorites()).toEqual([]);
    expect(toggleGuestFavorite("a")).toBe(true);
    expect(toggleGuestFavorite("b")).toBe(true);
    expect(toggleGuestFavorite("a")).toBe(false);
    expect(readGuestFavorites()).toEqual(["b"]);
    clearGuestFavorites();
    expect(readGuestFavorites()).toEqual([]);
  });

  it("survives garbage in storage", () => {
    localStorage.setItem("studlenta:favorites", "{not json");
    expect(readGuestFavorites()).toEqual([]);
    localStorage.setItem("studlenta:favorites", JSON.stringify([1, "ok", null]));
    expect(readGuestFavorites()).toEqual(["ok"]);
  });
});
