import { expect, test } from "@playwright/test";
import { createEvent, expectAccessible, inDays, lastLetterLink, login, logout, register, uniq } from "./helpers";

const moderatorEmail = () => process.env.E2E_MODERATOR_EMAIL ?? "mod-e2e@uust.ru";

test("путь заявки: автор → модератор → лента, уведомление и превью для соцсетей", async ({ page }) => {
  const id = uniq();
  const title = `Вечер музыки ${id}`;

  await register(page, "Иван Петров", `ivan-${id}@uust.ru`);
  await createEvent(page, title, { cover: true });
  const mine = page.getByRole("article", { name: title });
  await expect(mine.getByText("На проверке")).toBeVisible();
  await expectAccessible(page, "Мои публикации");

  // До одобрения событие не видно в ленте
  await page.goto(`./?q=${encodeURIComponent(id)}`);
  await expect(page.getByText("Событий нет", { exact: true })).toBeVisible();
  await logout(page);

  await login(page, moderatorEmail());
  await page.goto("moderation");
  await page.getByRole("button", { name: new RegExp(title) }).click();
  await page.getByRole("button", { name: "Одобрить" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "отметьте все пункты" })).toBeVisible();
  await expectAccessible(page, "Модерация");
  for (const box of await page.getByRole("checkbox").all()) await box.check();
  await page.getByRole("button", { name: "Одобрить" }).click();
  await expect(page.getByRole("status").filter({ hasText: `Опубликовано: «${title}»` })).toBeVisible();
  await logout(page);

  // Публично: лента, страница события, метаданные для превью
  await page.goto(`./?q=${encodeURIComponent(id)}`);
  const card = page.getByRole("article", { name: title });
  await expect(card).toBeVisible();
  await expect(card.getByRole("img")).toHaveCount(0); // обложка в карточке декоративная (alt="")
  await card.getByRole("link", { name: title }).click();
  await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
  await expect(page.getByText(/Проверено модератором/)).toBeVisible();
  await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", title);
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", /\/studlenta\/media\/covers\//);
  await expectAccessible(page, "Страница события");

  // Автор видит уведомление о публикации
  await login(page, `ivan-${id}@uust.ru`);
  await page.getByRole("button", { name: "Уведомления, новых: 1" }).click();
  await expect(page.getByRole("region", { name: "Уведомления" })).toContainText(`Событие «${title}» опубликовано`);
});

test("модератор возвращает на доработку — автор видит комментарий и исправляет", async ({ page }) => {
  const id = uniq();
  const title = `Турнир ${id}`;
  await register(page, "Анастасия Кузнецова", `nastya-${id}@uust.ru`);
  await createEvent(page, title, { category: "Спорт" });
  await logout(page);

  await login(page, moderatorEmail());
  await page.goto("moderation");
  await page.getByRole("button", { name: new RegExp(title) }).click();
  await page.getByRole("button", { name: "Вернуть на доработку" }).click();
  await expect(page.getByLabel(/Комментарий автору/)).toHaveAttribute("aria-invalid", "true");
  await page.getByLabel(/Комментарий автору/).fill("Укажите время окончания");
  await page.getByRole("button", { name: "Вернуть на доработку" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Возвращено на доработку" })).toBeVisible();
  await logout(page);

  await login(page, `nastya-${id}@uust.ru`);
  await page.goto("my");
  const item = page.getByRole("article", { name: title });
  await expect(item.getByText("Нужны правки")).toBeVisible();
  await expect(item).toContainText("Укажите время окончания");
  await item.getByRole("link", { name: "Исправить" }).click();
  await expect(page.getByRole("note")).toContainText("Укажите время окончания");
  await page.getByLabel("Окончание").fill(inDays(3, 22));
  await page.getByRole("button", { name: "Отправить на модерацию" }).click();
  await expect(page.getByRole("article", { name: title }).getByText("На проверке")).toBeVisible();
});

test("подтверждение почты: баннер, запрет отправки, ссылка из письма", async ({ page }) => {
  const id = uniq();
  const email = `verify-${id}@uust.ru`;
  await register(page, "Вера Почтова", email, { verify: false });
  const banner = page.getByRole("region", { name: "Подтвердите почту" });
  await expect(banner).toContainText(email);
  await expectAccessible(page, "Лента с баннером подтверждения");

  await page.goto("my/new");
  await page.getByLabel("Заголовок", { exact: false }).fill(`Неподтверждённое ${id}`);
  await page.getByRole("button", { name: "Отправить на модерацию" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Подтвердите почту" })).toBeVisible();

  await expect.poll(() => { try { return lastLetterLink(email); } catch { return ""; } }).toContain("token=");
  await page.goto(lastLetterLink(email));
  await expect(page.getByText("Готово, почта подтверждена")).toBeVisible();
  await page.goto("./");
  await expect(banner).toBeHidden();
});

test("восстановление пароля по ссылке из письма", async ({ page }) => {
  const id = uniq();
  const email = `forgot-${id}@uust.ru`;
  await register(page, "Забывчивый Студент", email);
  await logout(page);

  await page.goto("login");
  await page.getByRole("link", { name: "Забыли пароль?" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Восстановление пароля" })).toBeVisible();
  await expectAccessible(page, "Восстановление пароля");
  await page.getByLabel("Почта").fill(email);
  await page.getByRole("button", { name: "Прислать ссылку" }).click();
  await expect(page.getByRole("status")).toContainText("Если такой аккаунт есть");

  await expect.poll(() => { try { return lastLetterLink(email, "reset-password"); } catch { return ""; } }).toContain("token=");
  await page.goto(lastLetterLink(email, "reset-password"));
  await page.getByLabel("Новый пароль").fill("brand-new-pass");
  await page.getByRole("button", { name: "Сохранить пароль" }).click();
  await expect(page.getByText("Пароль изменён")).toBeVisible();

  await page.goto("login");
  await page.getByLabel("Почта").fill(email);
  await page.getByLabel("Пароль", { exact: true }).fill("brand-new-pass");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("button", { name: /^Уведомления/ })).toBeVisible();
});

test("форма показывает ошибки у полей и не теряет данные", async ({ page }) => {
  const id = uniq();
  await register(page, "Пётр Ошибкин", `err-${id}@uust.ru`);
  await page.goto("my/new");
  await page.getByLabel("Заголовок", { exact: false }).fill("Ква");
  await page.getByRole("button", { name: "Отправить на модерацию" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Заполните поля" })).toBeVisible();
  const titleInput = page.getByLabel("Заголовок", { exact: false });
  await expect(titleInput).toHaveAttribute("aria-invalid", "true");
  await expect(titleInput).toBeFocused();
  await expect(titleInput).toHaveValue("Ква");
  await expectAccessible(page, "Форма с ошибками");
});

test("гость: лента, фильтры, лайк просит войти, избранное без входа", async ({ page }) => {
  await page.goto("./");
  await expect(page.getByRole("heading", { level: 1, name: "Лента событий" })).toBeVisible();
  await expectAccessible(page, "Лента");

  const upcoming = page.getByRole("region", { name: "Ближайшие" });
  await expect(upcoming.getByRole("listitem").first()).toBeVisible();
  await upcoming.getByRole("button", { name: "Прокрутить вперёд" }).click();
  await upcoming.getByRole("link").first().click();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.goBack();

  await page.getByRole("group", { name: "Когда" }).getByRole("button", { name: "Сегодня" }).click();
  await expect(page).toHaveURL(/period=today/);
  await page.getByRole("group", { name: "Когда" }).getByRole("button", { name: "Все" }).click();

  const first = page.getByRole("article").first();
  await expect(first).toBeVisible();
  await first.getByRole("button", { name: /^Нравится/ }).click();
  await expect(page.getByRole("status").filter({ hasText: "Чтобы ставить лайки" })).toBeVisible();

  const title = await first.getByRole("heading").innerText();
  await first.getByRole("button", { name: "Добавить в избранное" }).click();
  await expect(first.getByRole("button", { name: "Убрать из избранного" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("navigation", { name: "Разделы" }).getByRole("link", { name: "Избранное" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Избранное" })).toBeVisible();
  await expect(page.getByRole("article", { name: title })).toBeVisible();
});

test("скин сохраняется после перезагрузки и тёмная тема проходит WCAG", async ({ page }) => {
  await page.goto("./");
  const skins = page.getByRole("group", { name: "Скин" });
  await skins.getByRole("radio", { name: "Тёмная" }).check();
  await expect(page.locator("html")).toHaveAttribute("data-skin", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-skin", "dark");
  await expect(skins.getByRole("radio", { name: "Тёмная" })).toBeChecked();
  await expectAccessible(page, "Лента, тёмный скин");
  await skins.getByRole("radio", { name: "Тёмная" }).focus();
  await page.keyboard.press("ArrowDown"); // нативные radio: стрелки переключают скин
  await expect(page.locator("html")).toHaveAttribute("data-skin", "green");
});

test("календарь управляется с клавиатуры", async ({ page }) => {
  await page.goto("calendar");
  await expect(page.getByRole("heading", { level: 1, name: "Календарь" })).toBeVisible();
  const selected = page.locator('[role="gridcell"][aria-selected="true"] button');
  await selected.focus();
  const before = await selected.getAttribute("data-date");
  await page.keyboard.press("ArrowRight");
  await expect(page.locator('[role="gridcell"][aria-selected="true"] button')).not.toHaveAttribute("data-date", before ?? "");
  await expect(page.locator('[role="gridcell"][aria-selected="true"] button')).toBeFocused();
  await expectAccessible(page, "Календарь");
});

test("страница «О проекте» и вход доступны", async ({ page }) => {
  await page.goto("about");
  await expectAccessible(page, "О проекте");
  await page.goto("login");
  await expectAccessible(page, "Вход");
  await page.getByLabel("Почта").fill("nobody@uust.ru");
  await page.getByLabel("Пароль", { exact: true }).fill("wrong-pass");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Неверная почта или пароль" })).toBeVisible();
});
