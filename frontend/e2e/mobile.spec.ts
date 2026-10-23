import { expect, test } from "@playwright/test";
import { expectAccessible } from "./helpers";

test("на телефоне — нижний таб-бар и полоса категорий вместо сайдбара", async ({ page }) => {
  await page.goto("./");
  await expect(page.getByRole("complementary", { name: "Навигация" })).toBeHidden();
  const tabs = page.getByRole("navigation", { name: "Разделы" });
  await expect(tabs.getByRole("link", { name: "Календарь" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Категории" }).getByRole("link", { name: "Все" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow, "нет горизонтальной прокрутки страницы").toBe(false);
  await expectAccessible(page, "Лента на телефоне");
  await tabs.getByRole("link", { name: "Календарь" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Календарь" })).toBeVisible();
});
