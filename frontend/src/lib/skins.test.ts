import { describe, expect, it } from "vitest";
import { DEFAULT_SKIN, SKINS, applySkin, readSkin, saveSkin } from "./skins";

describe("skins", () => {
  it("offers the four skins from the design", () => {
    expect(SKINS.map((s) => s.id)).toEqual(["light", "dark", "green", "violet"]);
    expect(DEFAULT_SKIN).toBe("light");
  });

  it("persists the choice and ignores unknown values", () => {
    expect(readSkin()).toBe("light");
    saveSkin("violet");
    expect(readSkin()).toBe("violet");
    localStorage.setItem("studlenta:skin", "neon");
    expect(readSkin()).toBe("light");
  });

  it("applies the skin to the root element", () => {
    applySkin("dark");
    expect(document.documentElement.dataset.skin).toBe("dark");
    expect(document.documentElement.style.colorScheme).toBe("dark");
    applySkin("green");
    expect(document.documentElement.style.colorScheme).toBe("light");
  });
});
