import { describe, expect, it } from "vitest";
import { dayKey, formatDayTitle, formatWhen, formatWhenInline, isToday } from "./format";

// Пятница, 23 октября 2026, 12:00 по Уфе (07:00 UTC)
const NOW = new Date("2026-10-23T07:00:00Z");

describe("formatWhen", () => {
  it.each([
    ["2026-10-23T13:00:00Z", "Сегодня, 18:00"],
    ["2026-10-24T05:00:00Z", "Завтра, 10:00"],
    ["2026-10-25T10:00:00Z", "25 окт, 15:00"],
    ["2026-11-01T05:00:00Z", "1 ноя, 10:00"],
  ])("%s → %s", (iso, expected) => {
    expect(formatWhen(iso, NOW)).toBe(expected);
  });

  it("uses the university timezone, not UTC, for the day", () => {
    // 22 октября 20:30 UTC — это уже 23 октября 01:30 по Уфе
    expect(formatWhen("2026-10-22T20:30:00Z", NOW)).toBe("Сегодня, 01:30");
    expect(isToday("2026-10-22T20:30:00Z", NOW)).toBe(true);
    expect(dayKey("2026-10-22T20:30:00Z")).toBe("2026-10-23");
  });

  it("adds the year when it differs", () => {
    expect(formatWhen("2027-01-15T05:00:00Z", NOW)).toBe("15 янв 2027, 10:00");
  });
});

describe("formatDayTitle", () => {
  it("names today and the weekday", () => {
    expect(formatDayTitle("2026-10-23", NOW)).toBe("Сегодня, 23 октября, пятница");
    expect(formatDayTitle("2026-10-29", NOW)).toBe("29 октября, четверг");
  });
});

describe("formatWhenInline", () => {
  it("lowercases relative days for the middle of a sentence", () => {
    expect(formatWhenInline("2026-10-23T13:00:00Z", NOW)).toBe("сегодня, 18:00");
    expect(formatWhenInline("2026-10-25T10:00:00Z", NOW)).toBe("25 окт, 15:00");
  });
});
