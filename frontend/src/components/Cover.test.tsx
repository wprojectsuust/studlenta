import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Cover } from "./Cover";

const cat = { id: 1, slug: "concerts", name: "Концерты", color: "#7C3AED" };
const src = "/studlenta/media/covers/0b6e7c2e-1111-4222-8333-944455556666.jpg";

describe("Cover", () => {
  it("offers the 640px thumbnail to the browser via srcset", () => {
    const { container } = render(<Cover src={src} category={cat} sizes="220px" />);
    const img = container.querySelector("img")!;
    expect(img.getAttribute("srcset")).toBe(`${src.replace(".jpg", "-640.jpg")} 640w, ${src} 1600w`);
    expect(img.getAttribute("sizes")).toBe("220px");
    expect(img.getAttribute("loading")).toBe("lazy");
  });

  it("loads above-the-fold covers eagerly", () => {
    const { container } = render(<Cover src={src} category={cat} priority />);
    const img = container.querySelector("img")!;
    expect(img.getAttribute("loading")).toBe("eager");
    expect(img.getAttribute("fetchpriority")).toBe("high");
  });

  it("leaves foreign images without srcset", () => {
    const { container } = render(<Cover src="https://example.org/a.png" category={cat} />);
    expect(container.querySelector("img")!.hasAttribute("srcset")).toBe(false);
  });
});
