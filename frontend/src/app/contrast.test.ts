// WCAG 2.1 AA по токенам всех скинов: текст ≥ 4.5:1, границы полей и фокус ≥ 3:1 (1.4.3, 1.4.11).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// В jsdom import.meta.url не file:, поэтому путь от корня проекта (vitest запускается из frontend/).
const css = readFileSync(join(process.cwd(), "src/app/globals.css"), "utf8");

function block(selector: RegExp): Record<string, string> {
  const match = css.match(selector);
  if (!match?.[1]) throw new Error(`нет блока ${selector}`);
  return Object.fromEntries([...match[1].matchAll(/--color-([\w-]+):\s*(#[0-9a-fA-F]{6})/g)].map((m) => [m[1], m[2]!]));
}

const light = block(/:root,\s*:root\[data-skin="light"\]\s*\{([^}]*)\}/);
const skins: Record<string, Record<string, string>> = {
  light,
  dark: block(/:root\[data-skin="dark"\]\s*\{([^}]*)\}/),
  green: { ...light, ...block(/:root\[data-skin="green"\]\s*\{([^}]*)\}/) },
  violet: { ...light, ...block(/:root\[data-skin="violet"\]\s*\{([^}]*)\}/) },
};

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
const ratio = (a: string, b: string) => {
  const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p) as [number, number];
  return (x + 0.05) / (y + 0.05);
};

const TEXT: [string, string][] = [
  ["ink", "bg"], ["ink", "surface"], ["ink", "chip"], ["muted", "bg"], ["muted", "surface"], ["muted", "chip"],
  ["accent-text", "surface"], ["accent-text", "bg"], ["on-accent", "accent"], ["on-side", "side"], ["on-side", "side-active"],
  ["side-muted", "side"], ["side-muted", "side-active"], ["danger", "surface"], ["like", "surface"], ["fav", "surface"],
  ["success-ink", "success-bg"], ["warning-ink", "warning-bg"], ["danger-ink", "danger-bg"], ["info-ink", "info-bg"],
];
const NON_TEXT: [string, string][] = [["field-border", "surface"], ["focus", "surface"], ["focus", "bg"]];
const CATEGORY = ["#7C3AED", "#15803D", "#1D4ED8", "#C2410C", "#BE185D", "#0E7490", "#4B5563"];

describe.each(Object.entries(skins))("скин %s", (_, t) => {
  it.each(TEXT)("текст %s на %s ≥ 4.5:1", (fg, bg) => {
    expect(t[fg], fg).toBeDefined();
    expect(ratio(t[fg]!, t[bg]!)).toBeGreaterThanOrEqual(4.5);
  });
  it.each(NON_TEXT)("%s на %s ≥ 3:1", (fg, bg) => {
    expect(ratio(t[fg]!, t[bg]!)).toBeGreaterThanOrEqual(3);
  });
});

it.each(CATEGORY)("белый текст на категории %s ≥ 4.5:1", (color) => {
  expect(ratio("#FFFFFF", color)).toBeGreaterThanOrEqual(4.5);
});
