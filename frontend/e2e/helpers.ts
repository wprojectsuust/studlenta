import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";
import { deflateSync } from "node:zlib";

export const PASSWORD = "password1";
export const uniq = () => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

/** Значение для datetime-local: через N дней в 19:00 по Уфе. */
export function inDays(days: number, hour = 19): string {
  const d = new Date(Date.now() + days * 86_400_000);
  const ufa = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Yekaterinburg", year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
  return `${ufa}T${String(hour).padStart(2, "0")}:00`;
}

/** Обложка 1600×900 (PNG) — достаточно для проверки сервером ширины ≥ 1200. */
export function coverPng(): Buffer {
  // 1x1 не пройдёт проверку ширины — генерируем настоящий PNG нужного размера.
  const width = 1600, height = 900;
  const row = Buffer.alloc(1 + width * 3);
  for (let x = 0; x < width; x++) row.writeUIntBE(0x2b59e0, 1 + x * 3, 3);
  const raw = Buffer.concat(Array.from({ length: height }, () => row));
  const crcTable = Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  const crc = (buf: Buffer) => { let c = 0xffffffff; for (const b of buf) c = crcTable[(c ^ b) & 0xff]! ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (type: string, data: Buffer) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const body = Buffer.concat([Buffer.from(type), data]);
    const sum = Buffer.alloc(4); sum.writeUInt32BE(crc(body));
    return Buffer.concat([len, body, sum]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0); ihdr.writeUInt32BE(height, 4); ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", ihdr), chunk("IDAT", deflateSync(raw)), chunk("IEND", Buffer.alloc(0))]);
}

export async function expectAccessible(page: Page, label: string) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const summary = results.violations.map((v) => `${v.id}: ${v.help} → ${v.nodes.map((n) => n.target.join(" ")).slice(0, 3).join(" | ")}`);
  expect(summary, `axe на «${label}»`).toEqual([]);
}

export async function register(page: Page, name: string, email: string) {
  await page.goto("login?mode=register");
  await page.getByLabel("Имя и фамилия").fill(name);
  await page.getByLabel("Почта").fill(email);
  await page.getByLabel("Пароль", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Зарегистрироваться" }).click();
  await expect(page.getByRole("link", { name: `профиль: ${name}` })).toBeVisible();
}

export async function login(page: Page, email: string) {
  await page.goto("login");
  await page.getByLabel("Почта").fill(email);
  await page.getByLabel("Пароль", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("button", { name: /^Уведомления/ })).toBeVisible();
}

export async function logout(page: Page) {
  await page.goto("my");
  await page.getByRole("button", { name: "Выйти" }).click();
  await expect(page.getByRole("link", { name: "Войти" })).toBeVisible();
}

/** Автор создаёт событие и отправляет его на модерацию. */
export async function createEvent(page: Page, title: string, opts: { days?: number; category?: string; cover?: boolean } = {}) {
  await page.goto("my/new");
  await page.getByLabel("Заголовок", { exact: false }).fill(title);
  await page.getByLabel("Категория", { exact: false }).selectOption({ label: opts.category ?? "Концерты" });
  await page.getByLabel("Краткий анонс", { exact: false }).fill("Живой звук, любимые хиты и атмосфера студенческого концерта.");
  await page.getByLabel("Описание", { exact: false }).fill("Группа «Путь» и приглашённые гости выступят в актовом зале.\n\nВход свободный.");
  await page.getByLabel("Начало", { exact: false }).fill(inDays(opts.days ?? 3));
  await page.getByLabel("Место проведения", { exact: false }).fill("Актовый зал УУНиТ");
  if (opts.cover) {
    await page.getByLabel("Обложка").setInputFiles({ name: "cover.png", mimeType: "image/png", buffer: coverPng() });
    await expect(page.getByAltText("Выбранная обложка")).toBeVisible();
  }
  await page.getByRole("button", { name: "Отправить на модерацию" }).click();
  await expect(page.getByRole("heading", { name: "Мои публикации" })).toBeVisible();
}
