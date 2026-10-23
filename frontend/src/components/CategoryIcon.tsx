// Значки категорий: линейная иконка на плашке цвета категории (тот же цвет, что у тегов).
// Белая иконка на любой заливке палитры даёт контраст ≥ 4.5:1.

export const CATEGORY_ICONS: Record<string, string> = {
  concerts: "M9 18V5l11-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM20 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z",
  sport: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3.5 9.5c5 0 9 3 10.5 11M20.5 9.5c-5 0-9 3-10.5 11M12 3c-2 3-2 6 0 9",
  science: "M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3M7.5 15h9",
  volunteering: "M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10zM9 11h6M12 8v6",
  culture: "M4 4h16v7a8 8 0 0 1-16 0zM9 9h.01M15 9h.01M9 13c1.5 1.5 4.5 1.5 6 0",
  entertainment: "M6 9h12a4 4 0 0 1 0 8 3 3 0 0 1-2.5-1.3L14 14h-4l-1.5 1.7A3 3 0 0 1 6 17a4 4 0 0 1 0-8zM8 11v3M6.5 12.5h3M16 12h.01M17.5 13.5h.01",
  other: "M12 3l2.4 5.6L20 9.2l-4.3 3.9 1.3 5.9L12 16l-5 3 1.3-5.9L4 9.2l5.6-.6z",
};

type Props = { slug: string; color: string; size?: number };

export function CategoryIcon({ slug, color, size = 26 }: Props) {
  const path = CATEGORY_ICONS[slug] ?? CATEGORY_ICONS.other;
  return (
    <span style={{ width: size, height: size, flex: "none", display: "inline-grid", placeItems: "center", borderRadius: Math.round(size / 3.5), backgroundColor: color, color: "#FFFFFF" }}>
      <svg width={size * 0.62} height={size * 0.62} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}
        strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
        <path d={path} />
      </svg>
    </span>
  );
}
