// Анонимный id браузера для рекомендаций гостю: случайный UUID, без персональных данных (ADR-0014).
const KEY = "studlenta:visitor";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

let fallback: string | null = null; // если localStorage недоступен — id живёт до перезагрузки

export function visitorId(): string {
  try {
    const stored = window.localStorage.getItem(KEY);
    if (stored && UUID.test(stored)) return stored;
    const id = crypto.randomUUID();
    window.localStorage.setItem(KEY, id);
    return id;
  } catch {
    fallback ??= crypto.randomUUID();
    return fallback;
  }
}
