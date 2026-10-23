// Все даты показываем по времени университета: «сегодня» — это сегодня в Уфе, а не в UTC.
export const UNIVERSITY_TZ = "Asia/Yekaterinburg";

const MONTHS_SHORT = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];
const MONTHS_GENITIVE = [
  "января", "февраля", "марта", "апреля", "мая", "июня",
  "июля", "августа", "сентября", "октября", "ноября", "декабря",
];
const WEEKDAYS = ["воскресенье", "понедельник", "вторник", "среда", "четверг", "пятница", "суббота"];

const partsFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: UNIVERSITY_TZ,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  weekday: "short",
  hourCycle: "h23",
});

type Parts = { year: number; month: number; day: number; time: string; weekday: number };
const WEEKDAY_INDEX: Record<string, number> = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };

function parts(date: Date): Parts {
  const p = Object.fromEntries(partsFormatter.formatToParts(date).map((x) => [x.type, x.value]));
  return {
    year: Number(p.year),
    month: Number(p.month),
    day: Number(p.day),
    time: `${p.hour}:${p.minute}`,
    weekday: WEEKDAY_INDEX[p.weekday ?? "Sun"] ?? 0,
  };
}

const toDate = (value: string | Date) => (typeof value === "string" ? new Date(value) : value);

/** Ключ дня ГГГГ-ММ-ДД по времени университета. */
export function dayKey(value: string | Date): string {
  const { year, month, day } = parts(toDate(value));
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

export function isToday(value: string | Date, now = new Date()): boolean {
  return dayKey(value) === dayKey(now);
}

export function formatTime(value: string | Date): string {
  return parts(toDate(value)).time;
}

/** «Сегодня, 18:00», «Завтра, 10:00», «25 окт, 15:00», «15 янв 2027, 10:00». */
export function formatWhen(value: string | Date, now = new Date()): string {
  const date = toDate(value);
  const p = parts(date);
  const key = dayKey(date);
  if (key === dayKey(now)) return `Сегодня, ${p.time}`;
  if (key === dayKey(new Date(now.getTime() + 86_400_000))) return `Завтра, ${p.time}`;
  const year = p.year === parts(now).year ? "" : ` ${p.year}`;
  return `${p.day} ${MONTHS_SHORT[p.month - 1]}${year}, ${p.time}`;
}

/** Для середины фразы: «проверено модератором сегодня, 16:24». */
export function formatWhenInline(value: string | Date, now = new Date()): string {
  const text = formatWhen(value, now);
  return text.startsWith("Сегодня") || text.startsWith("Завтра") ? text[0]!.toLowerCase() + text.slice(1) : text;
}

/** «Сегодня, 23 октября, пятница» для заголовка дня в календаре. */
export function formatDayTitle(key: string, now = new Date()): string {
  const [year, month, day] = key.split("-").map(Number) as [number, number, number];
  const noonUtc = new Date(Date.UTC(year, month - 1, day, 7)); // 12:00 по Уфе
  const title = `${day} ${MONTHS_GENITIVE[month - 1]}, ${WEEKDAYS[parts(noonUtc).weekday]}`;
  return key === dayKey(now) ? `Сегодня, ${title}` : title;
}

export function monthTitle(year: number, month: number): string {
  const name = new Intl.DateTimeFormat("ru-RU", { month: "long", timeZone: "UTC" }).format(
    new Date(Date.UTC(year, month - 1, 1)),
  );
  return `${name[0]?.toUpperCase()}${name.slice(1)} ${year}`;
}

// Уфа живёт в UTC+5 без перехода на летнее время (с 2014 года), поэтому смещение фиксированное.
const UNIVERSITY_OFFSET = "+05:00";

/** ISO → значение для <input type="datetime-local"> по времени университета. */
export function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  const p = Object.fromEntries(partsFormatter.formatToParts(date).map((x) => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}

/** Значение datetime-local (время университета) → ISO со смещением. */
export function fromLocalInput(value: string): string | null {
  return value ? `${value}:00${UNIVERSITY_OFFSET}` : null;
}
