import type { Category } from "@/lib/api";

/** Цвет категории приходит с API и ограничен палитрой с контрастом белого текста ≥ 4.5:1. */
export function TagPill({ category }: { category: Category }) {
  return (
    <span style={{ display: "inline-block", padding: "2px 10px", borderRadius: 999, background: category.color, color: "#FFFFFF", fontSize: 13, fontWeight: 600, lineHeight: 1.5 }}>
      {category.name}
    </span>
  );
}
