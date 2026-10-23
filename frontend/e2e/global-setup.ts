import { execFileSync } from "node:child_process";
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
  const author = await call("/auth/register", { method: "POST", body: { email: `seed-${stamp}@uust.ru`, password: "password1", full_name: "Студсовет УУНиТ" } });
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
