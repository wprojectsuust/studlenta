"use client";

import { useSyncExternalStore } from "react";
import { SKINS, applySkin, readSkin, saveSkin, subscribeSkin } from "@/lib/skins";

export function SkinPicker({ onDark = true }: { onDark?: boolean }) {
  const skin = useSyncExternalStore(subscribeSkin, readSkin, () => null);

  return (
    <div role="group" aria-label="Скин" style={{ display: "flex", gap: 8 }}>
      {SKINS.map((s) => {
        const on = s.id === skin;
        return (
          <button key={s.id} type="button" aria-pressed={on} aria-label={`Скин: ${s.name}`} title={s.name}
            onClick={() => { saveSkin(s.id); applySkin(s.id); }}
            style={{ width: 44, height: 44, padding: 0, borderRadius: 12, display: "grid", placeItems: "center", background: s.swatch,
              border: `2px solid ${on ? (onDark ? "var(--color-on-side)" : "var(--color-ink)") : "transparent"}` }}>
            <span style={{ width: 18, height: 18, borderRadius: 999, background: s.dot }} />
          </button>
        );
      })}
    </div>
  );
}
