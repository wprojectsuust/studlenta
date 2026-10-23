import { describe, expect, it } from "vitest";
import { visitorId } from "./visitor";

describe("visitorId", () => {
  it("creates a random id once and then keeps it", () => {
    localStorage.clear();
    const first = visitorId();
    expect(first).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(visitorId()).toBe(first);
  });

  it("replaces garbage in storage", () => {
    localStorage.setItem("studlenta:visitor", "<script>");
    expect(visitorId()).not.toBe("<script>");
  });
});
