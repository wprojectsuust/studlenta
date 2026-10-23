/* eslint-disable @next/next/no-img-element -- обложки отдаёт API; оптимизатор next/image на VPS с 1 ГБ памяти не нужен */
import type { CSSProperties } from "react";
import type { Category } from "@/lib/api";
import { CapIcon } from "./icons";

type Props = {
  src: string | null;
  category: Category;
  alt?: string;
  className?: string;
  style?: CSSProperties;
  /** Ширина картинки в вёрстке — браузер выберет превью 640 px или полную 1600 px. */
  sizes?: string;
  /** Первые карточки на экране: грузим сразу и с высоким приоритетом (LCP). */
  priority?: boolean;
};

// Сервер кладёт рядом с обложкой превью «-640» (ADR-0013).
const OWN_COVER = /\/media\/covers\/[0-9a-f-]{36}\.jpg$/;

/** Обложка события или плашка цвета категории, если обложки нет. */
export function Cover({ src, category, alt = "", className, style, sizes = "100vw", priority = false }: Props) {
  if (src) {
    const srcSet = OWN_COVER.test(src) ? `${src.replace(/\.jpg$/, "-640.jpg")} 640w, ${src} 1600w` : undefined;
    return (
      <img src={src} srcSet={srcSet} sizes={srcSet ? sizes : undefined} alt={alt} className={className}
        style={{ objectFit: "cover", ...style }} loading={priority ? "eager" : "lazy"}
        fetchPriority={priority ? "high" : undefined} decoding="async" />
    );
  }
  return (
    <div data-cover-fallback className={className} style={{ backgroundColor: category.color, color: "#FFFFFF", display: "grid", placeItems: "center", ...style }}
      role={alt ? "img" : undefined} aria-label={alt || undefined}>
      <CapIcon size={40} style={{ opacity: 0.85 }} />
    </div>
  );
}
