import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { SkinPicker } from "./SkinPicker";

describe("SkinPicker", () => {
  it("is a labelled radio group with names, not colour dots", async () => {
    render(<SkinPicker />);
    const group = screen.getByRole("group", { name: "Скин" });
    expect(group.tagName).toBe("FIELDSET");
    const radios = screen.getAllByRole("radio");
    expect(radios.map((r) => r.getAttribute("value"))).toEqual(["light", "dark", "green", "violet"]);
    expect(screen.getByRole("radio", { name: "Светлая" })).toBeChecked();

    await userEvent.click(screen.getByRole("radio", { name: "Тёмная" }));
    expect(document.documentElement.dataset.skin).toBe("dark");
    expect(screen.getByRole("radio", { name: "Тёмная" })).toBeChecked();
    expect(localStorage.getItem("studlenta:skin")).toBe("dark");
  });
});
