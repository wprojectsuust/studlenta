"use client";

import { useSyncExternalStore } from "react";
import { applySkin, readSkin, saveSkin, subscribeSkin, SKINS, type SkinId } from "@/lib/skins";
import styles from "./SkinPicker.module.css";

const ICONS: Record<SkinId, string> = {
  light: "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  dark: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z",
  green: "M5 19c0-9 6-14 15-14 0 9-5 14-14 14zM5 19l8-8",
  violet: "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z",
};

/** Нативные radio: стрелки на клавиатуре и скринридеры работают без дополнительного кода. */
export function SkinPicker({ tone = "side" }: { tone?: "side" | "page" }) {
  const current = useSyncExternalStore(subscribeSkin, readSkin, () => null);
  return (
    <fieldset className={`${styles.picker} ${tone === "side" ? styles.side : styles.page}`}>
      <legend className={styles.legend}>Скин</legend>
      <div className={styles.grid}>
        {SKINS.map((s) => (
          <label key={s.id} className={styles.option}>
            <input type="radio" name="skin" value={s.id} checked={current === s.id}
              onChange={() => { saveSkin(s.id); applySkin(s.id); }} />
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d={ICONS[s.id]} />
            </svg>
            {s.name}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
