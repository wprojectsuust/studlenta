import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

// Модератора создаёт CLI бэкенда — через HTTP API назначить роль нельзя (ADR-0002).
const MODERATOR = { email: "mod-e2e@uust.ru", name: "Елена Орлова", password: "password1" };
const BASE = (process.env.E2E_BASE_URL ?? "http://localhost:3000/studlenta/").replace(/\/$/, "");

function createModerator() {
  try {
    execFileSync("uv", ["run", "--no-sync", "studlenta-create-user", "--email", MODERATOR.email, "--name", MODERATOR.name, "--role", "moderator"], {
      cwd: join(__dirname, "../../backend"),
      env: { ...process.env, STUDLENTA_NEW_PASSWORD: MODERATOR.password },
      stdio: "pipe",
    });
  } catch (e) {
    if (!String((e as { stderr?: Buffer }).stderr ?? "").includes("Почта уже зарегистрирована")) throw e;
  }
}

/** Ссылку подтверждения берём из файлового «ящика» API (STUDLENTA_MAIL_OUTBOX_DIR). */
async function confirmEmail(email: string) {
  const dir = process.env.E2E_MAIL_OUTBOX ?? "/tmp/studlenta-mail";
  for (let i = 0; i < 50; i++) {
    let letters: { to: string; text: string }[] = [];
    try {
      letters = readdirSync(dir).filter((f) => f.endsWith(".json"))
        .map((f) => JSON.parse(readFileSync(join(dir, f), "utf8")) as { to: string; text: string });
    } catch {
      /* папки ещё нет — письмо в пути */
    }
    const token = letters.filter((l) => l.to === email).at(-1)?.text.match(/token=([\w-]+)/)?.[1];
    if (token) return void (await call("/auth/verify-email", { method: "POST", body: { token } }));
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error(`нет письма для ${email}`);
}

async function call(path: string, init: { method?: string; token?: string; body?: unknown } = {}) {
  const res = await fetch(`${BASE}/api/v1${path}`, {
    method: init.method ?? "GET",
    headers: { "content-type": "application/json", ...(init.token ? { authorization: `Bearer ${init.token}` } : {}) },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
  if (!res.ok) throw new Error(`${path}: ${res.status} ${await res.text()}`);
  return res.status === 204 ? null : res.json();
}

/** Одно опубликованное событие, чтобы сценарии гостя не зависели от порядка тестов. */
async function seedPublishedEvent() {
  const stamp = Date.now().toString(36);
  const email = `seed-${stamp}@uust.ru`;
  const author = await call("/auth/register", { method: "POST", body: { email, password: "password1", full_name: "Студсовет УУНиТ" } });
  await confirmEmail(email);
  const starts = new Date(Date.now() + 2 * 86_400_000).toISOString();
  const { id } = await call("/me/events", {
    method: "POST", token: author.access_token,
    body: { title: `Открытый микрофон ${stamp}`, summary: "Стихи, стендап, акустика — вход свободный.", body: "Выступить может любой студент: запишитесь у организаторов.",
      category_id: 1, place: "Студклуб, малый зал", starts_at: starts, ends_at: null, cover_url: null },
  });
  await call(`/me/events/${id}/submit`, { method: "POST", token: author.access_token });
  const mod = await call("/auth/login", { method: "POST", body: { email: MODERATOR.email, password: MODERATOR.password } });
  await call(`/moderation/events/${id}/approve`, { method: "POST", token: mod.access_token });
}

export default async function globalSetup() {
  createModerator();
  process.env.E2E_MODERATOR_EMAIL = MODERATOR.email;
  await seedPublishedEvent();
}
