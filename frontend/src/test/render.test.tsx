// Render every page with API data, then with deliberately broken versions of it.
// ESPN's feeds drift (fields go missing, turn null, lists come back empty), and
// a single throw while rendering blanks the whole page, so every page must
// survive all of these.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToString } from "react-dom/server";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import App from "../App";
import sample from "./api-sample.json";

type Json = unknown;

// Fields the backend always controls; everything else comes from ESPN and may be junk.
const KEEP = new Set(["id", "league", "state", "key", "kind", "today", "timezone", "date", "start_day", "espn_id", "leagues"]);

function mapStrings(v: Json, fn: (s: string, key: string) => Json, key = ""): Json {
  if (typeof v === "string") return KEEP.has(key) ? v : fn(v, key);
  if (Array.isArray(v)) return v.map((x) => mapStrings(x, fn, key));
  if (v && typeof v === "object")
    return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, mapStrings(x, fn, k)]));
  return v;
}

function mapArrays(v: Json, key = ""): Json {
  if (Array.isArray(v)) return key === "leagues" || key === "teams" || key === "games" || key === "tournaments" ? v.map((x) => mapArrays(x)) : [];
  if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, mapArrays(x, k)]));
  return v;
}

function dropKeys(v: Json, keys: string[]): Json {
  if (Array.isArray(v)) return v.map((x) => dropKeys(x, keys));
  if (v && typeof v === "object")
    return Object.fromEntries(
      Object.entries(v).map(([k, x]) => [k, keys.includes(k) ? null : dropKeys(x, keys)]),
    );
  return v;
}

const VARIANTS: Record<string, (d: typeof sample) => typeof sample> = {
  "as returned": (d) => d,
  "ESPN text fields null": (d) => ({ ...(mapStrings(d, () => null) as typeof sample), config: d.config }),
  "ESPN text fields empty": (d) => ({ ...(mapStrings(d, () => "") as typeof sample), config: d.config }),
  "nested lists empty": (d) => ({ ...(mapArrays(d) as typeof sample), config: d.config }),
  "odds, times, next game missing": (d) => ({
    ...(dropKeys(d, ["odds", "start", "end", "next_game", "rank", "over_under", "game"]) as typeof sample),
    config: d.config,
    game: d.game, // a detail with no game is a 404 from the API, not a render case
    game_epl: d.game_epl,
  }),
  "everything empty": (d) => ({
    ...d,
    scores: { date: d.scores.date, games: [], tournaments: [] },
    scoresToday: { date: d.scoresToday.date, games: [], tournaments: [] },
    schedule: { ...d.schedule, games: [], tournaments: [] },
    standings_nfl: { league: "nfl", groups: [], tournaments: [] },
    standings_pga: { league: "pga", groups: [], tournaments: [] },
    teams: [],
  }),
};

const PAGES: [string, string][] = [
  ["/", "scoresToday"],
  ["/?date=2026-10-03", "scores"],
  ["/schedule", "schedule"],
  ["/standings?league=nfl", "standings_nfl"],
  ["/standings?league=pga", "standings_pga"],
  ["/teams", "teams"],
  ["/game/nfl/401772001", "game"],
  ["/game/epl/740901", "game_epl"],
  ["/golf/pga/401703510", "golf"],
];

function render(url: string, d: typeof sample): string {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  qc.setQueryData(["config"], d.config);
  qc.setQueryData(["scores", "2026-10-02"], d.scoresToday);
  qc.setQueryData(["scores", "2026-10-03"], d.scores);
  qc.setQueryData(["schedule", d.config.schedule_days], d.schedule);
  qc.setQueryData(["standings", "nfl"], d.standings_nfl);
  qc.setQueryData(["standings", "pga"], d.standings_pga);
  qc.setQueryData(["teams"], d.teams);
  qc.setQueryData(["game", "nfl", "401772001"], d.game);
  qc.setQueryData(["game", "epl", "740901"], d.game_epl);
  qc.setQueryData(["golf", "pga", "401703510"], d.golf);
  return renderToString(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe.each(Object.entries(VARIANTS))("data: %s", (_name, variant) => {
  const d = variant(sample);
  it.each(PAGES)("%s renders", (url) => {
    const html = render(url, d);
    expect(html).toContain("sportsdash"); // the shell rendered
    expect(html).not.toContain("hit an error while rendering");
    expect(html).not.toContain("sk-row"); // data was used, not stuck loading
  });
});

it("real data shows real content", () => {
  const html = render("/?date=2026-10-03", sample);
  expect(html).toContain("Your teams");
  expect(html).toContain("Virginia");
  expect(html).toContain("UVA -3");
});
