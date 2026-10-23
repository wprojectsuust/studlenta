export type SkinId = "light" | "dark" | "green" | "violet";

export const SKINS: { id: SkinId; name: string; swatch: string; dot: string; scheme: "light" | "dark" }[] = [
  { id: "light", name: "Светлая", swatch: "#F3F5F9", dot: "#2B59E0", scheme: "light" },
  { id: "dark", name: "Тёмная", swatch: "#0D1117", dot: "#7896FF", scheme: "dark" },
  { id: "green", name: "Зелёная", swatch: "#F1F6F2", dot: "#1D7348", scheme: "light" },
  { id: "violet", name: "Фиолетовая", swatch: "#F6F4FB", dot: "#6438CC", scheme: "light" },
];
export const DEFAULT_SKIN: SkinId = "light";
const KEY = "studlenta:skin";
const isSkin = (v: unknown): v is SkinId => SKINS.some((s) => s.id === v);

export function readSkin(): SkinId {
  try {
    const value = localStorage.getItem(KEY);
    return isSkin(value) ? value : DEFAULT_SKIN;
  } catch {
    return DEFAULT_SKIN;
  }
}

export function saveSkin(id: SkinId): void {
  try {
    localStorage.setItem(KEY, id);
  } catch {
    /* скин просто не запомнится */
  }
}

export function applySkin(id: SkinId): void {
  const root = document.documentElement;
  root.dataset.skin = id;
  root.style.colorScheme = SKINS.find((s) => s.id === id)?.scheme ?? "light";
  window.dispatchEvent(new Event(SKIN_EVENT));
}

const SKIN_EVENT = "studlenta:skin";

/** Подписка для useSyncExternalStore: скин — внешнее состояние (атрибут <html> + localStorage). */
export function subscribeSkin(callback: () => void): () => void {
  window.addEventListener(SKIN_EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(SKIN_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

/** Выполняется в <head> до отрисовки, чтобы не мигал светлый скин у тех, кто выбрал тёмный. */
export const SKIN_BOOT_SCRIPT = `(function(){try{var s=localStorage.getItem(${JSON.stringify(KEY)});var ok=${JSON.stringify(
  SKINS.map((s) => s.id),
)};if(ok.indexOf(s)<0)s=${JSON.stringify(DEFAULT_SKIN)};var r=document.documentElement;r.dataset.skin=s;r.style.colorScheme=s==="dark"?"dark":"light";}catch(e){}})();`;
