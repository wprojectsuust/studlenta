/* eslint-disable @next/next/no-img-element -- обложки отдаёт API; оптимизатор next/image на VPS с 1 ГБ памяти не нужен */
import type { CSSProperties } from "react";
import type { Category } from "@/lib/api";
import { CapIcon } from "./icons";

type Props = { src: string | null; category: Category; alt?: string; className?: string; style?: CSSProperties };

/** Обложка события или плашка цвета категории, если обложки нет. */
export function Cover({ src, category, alt = "", className, style }: Props) {
  if (src) return <img src={src} alt={alt} className={className} style={{ objectFit: "cover", ...style }} loading="lazy" decoding="async" />;
  return (
    <div data-cover-fallback className={className} style={{ backgroundColor: category.color, color: "#FFFFFF", display: "grid", placeItems: "center", ...style }}
      role={alt ? "img" : undefined} aria-label={alt || undefined}>
      <CapIcon size={40} style={{ opacity: 0.85 }} />
    </div>
  );
}
