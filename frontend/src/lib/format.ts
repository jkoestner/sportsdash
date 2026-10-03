// Date and time formatting.
//
// Two kinds of values flow through the app:
//   * instants   – game start times, ISO strings in UTC from the API ("2026-10-03T19:30:00+00:00")
//   * calendar days – plain "YYYY-MM-DD" strings, already in the configured timezone
//
// Instants are shown in the configured timezone (config.yaml), not the browser's,
// so the dashboard reads the same on every device. Calendar days are pinned to
// noon UTC before formatting so no timezone can shift them to the wrong date.

const cache = new Map<string, Intl.DateTimeFormat>();

function fmt(timeZone: string, options: Intl.DateTimeFormatOptions, locale = "en-US"): Intl.DateTimeFormat {
  const key = locale + timeZone + JSON.stringify(options);
  let f = cache.get(key);
  if (!f) {
    f = new Intl.DateTimeFormat(locale, { timeZone, ...options });
    cache.set(key, f);
  }
  return f;
}

/** "3:30 PM" */
export function clock(iso: string | null, timeZone: string): string {
  if (!iso) return "TBD";
  return fmt(timeZone, { hour: "numeric", minute: "2-digit" }).format(new Date(iso));
}

/** The calendar day ("YYYY-MM-DD") an instant falls on in the given timezone. */
export function localDay(iso: string | null, timeZone: string): string | null {
  if (!iso) return null;
  // en-CA formats as YYYY-MM-DD.
  return fmt(timeZone, { year: "numeric", month: "2-digit", day: "2-digit" }, "en-CA").format(new Date(iso));
}

function noonUtc(day: string): Date {
  return new Date(`${day}T12:00:00Z`);
}

/** "2026-10-03" + 2 -> "2026-10-05" */
export function addDays(day: string, n: number): string {
  const d = noonUtc(day);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** "Sat" */
export function weekday(day: string): string {
  return fmt("UTC", { weekday: "short" }).format(noonUtc(day));
}

/** "Oct 3" */
export function monthDay(day: string): string {
  return fmt("UTC", { month: "short", day: "numeric" }).format(noonUtc(day));
}

/** "Sat, Oct 3" */
export function shortDay(day: string): string {
  return `${weekday(day)}, ${monthDay(day)}`;
}

/** "Saturday, October 3" */
export function longDay(day: string): string {
  return fmt("UTC", { weekday: "long", month: "long", day: "numeric" }).format(noonUtc(day));
}

/** "Oct 1–4" or "Sep 30–Oct 3" */
export function dayRange(startIso: string | null, endIso: string | null, timeZone: string): string {
  const s = localDay(startIso, timeZone);
  if (!s) return "";
  const e = localDay(endIso, timeZone) ?? s;
  if (s === e) return monthDay(s);
  return s.slice(0, 7) === e.slice(0, 7) ? `${monthDay(s)}–${Number(e.slice(8))}` : `${monthDay(s)}–${monthDay(e)}`;
}
