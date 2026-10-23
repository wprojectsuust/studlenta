// Иконки: inline-SVG, декоративные (aria-hidden) — подпись всегда даёт кнопка или текст рядом.
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };
function make(path: string, opts: { fill?: boolean } = {}) {
  return function Icon({ size = 20, ...props }: IconProps) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill={opts.fill ? "currentColor" : "none"} stroke="currentColor"
        strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" {...props}>
        <path d={path} />
      </svg>
    );
  };
}

export const FeedIcon = make("M4 5h16M4 12h16M4 19h10");
export const CalendarIcon = make("M3 5h18v16H3zM3 10h18M8 3v4M16 3v4");
export const BookmarkIcon = make("M6 3h12v18l-6-4-6 4z");
export const PenIcon = make("M4 20h4L19 9l-4-4L4 16zM13 7l4 4");
export const ShieldIcon = make("M12 3l8 3v6c0 4.5-3.5 8-8 9-4.5-1-8-4.5-8-9V6zM9 12l2 2 4-4");
export const InfoIcon = make("M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v5M12 8h.01");
export const HeartIcon = make("M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z");
export const ClockIcon = make("M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2");
export const PinIcon = make("M12 21s-7-6.5-7-12a7 7 0 0 1 14 0c0 5.5-7 12-7 12zM12 11.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z");
export const SearchIcon = make("M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-3.5-3.5");
export const BellIcon = make("M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10 21a2 2 0 0 0 4 0");
export const PlusIcon = make("M12 5v14M5 12h14");
export const ChevronLeft = make("M15 6l-6 6 6 6");
export const ChevronRight = make("M9 6l6 6-6 6");
export const BackIcon = make("M19 12H5M11 6l-6 6 6 6");
export const UserIcon = make("M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c1-4 4.5-6 8-6s7 2 8 6");
export const LinkIcon = make("M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1");
export const UploadIcon = make("M12 16V4M7 9l5-5 5 5M4 16v4h16v-4");
export const CheckIcon = make("M5 12l5 5L20 7");
export const CapIcon = make("M2 9l10-5 10 5-10 5zM6 11v5c2 2 10 2 12 0v-5M22 9v6");
export const ChartIcon = make("M4 20V10M10 20V4M16 20v-7M22 20H2");
export const TicketIcon = make("M3 9a2 2 0 0 0 0 6v4h18v-4a2 2 0 0 0 0-6V5H3zM14 5v14");
