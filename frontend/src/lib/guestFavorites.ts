// Избранное гостя живёт в localStorage; после входа переносится на сервер (/me/favorites/sync).
const KEY = "studlenta:favorites";

function safeStorage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null; // приватный режим, запрет cookies
  }
}

export function readGuestFavorites(): string[] {
  try {
    const raw: unknown = JSON.parse(safeStorage()?.getItem(KEY) ?? "[]");
    return Array.isArray(raw) ? raw.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

/** Возвращает новое состояние: true — добавлено. */
export function toggleGuestFavorite(id: string): boolean {
  const current = readGuestFavorites();
  const added = !current.includes(id);
  const next = added ? [...current, id] : current.filter((x) => x !== id);
  try {
    safeStorage()?.setItem(KEY, JSON.stringify(next));
  } catch {
    /* хранилище недоступно — избранное просто не запомнится */
  }
  return added;
}

export function clearGuestFavorites(): void {
  try {
    safeStorage()?.removeItem(KEY);
  } catch {
    /* ничего страшного */
  }
}
