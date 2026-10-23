import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CategoryIcon, CATEGORY_ICONS } from "./CategoryIcon";

describe("CategoryIcon", () => {
  it("has an icon for every seeded category and a fallback", () => {
    for (const slug of ["concerts", "sport", "science", "volunteering", "culture", "entertainment", "other"]) {
      expect(CATEGORY_ICONS[slug], slug).toBeDefined();
    }
    const { container } = render(<CategoryIcon slug="unknown" />);
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("is a plain icon without a coloured tile", () => {
    const { container } = render(<CategoryIcon slug="sport" />);
    const svg = container.firstElementChild!;
    expect(svg.tagName.toLowerCase()).toBe("svg");
    expect(svg).toHaveAttribute("stroke", "currentColor");
  });

  it("can be tinted when the colour carries meaning (calendar legend)", () => {
    const { container } = render(<CategoryIcon slug="sport" color="#15803D" />);
    expect(container.firstElementChild).toHaveAttribute("stroke", "#15803D");
  });
});
