# sportsdash

A self-hosted scores, schedule and standings dashboard. It runs a React +
TypeScript frontend (Vite) on top of a small Python API (FastAPI).

Out of the box it follows **NFL, NCAAF, NCAAB, EPL and the PGA Tour**, with
**Virginia (football + basketball)** and the **Dallas Cowboys** pinned as your teams.
Every game shows its time, venue, TV and betting lines, and each one opens to a
box score.

Data comes from ESPN's public JSON feeds (no API key). They're unofficial and
change without notice; see [ESPN quirks](#espn-quirks).

```
sportsdash/
  config.yaml          leagues and teams (shared by everything)
  backend/             Python: ESPN client, adapters, FastAPI JSON API
  frontend/            React + TypeScript app (Vite)
  Dockerfile           builds both into one image
  docker-compose.yml
```

## Run it on the homelab

```bash
docker compose up -d --build
```

## Develop on Windows

You need Python 3.11+ and Node 20.19+ (Vite 8's minimum; check with `node -v`).
Use two terminals.

**Terminal 1, the API** (http://localhost:8000/api/docs lists every endpoint):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn sportsdash.api:app --reload --port 8000
```

**Terminal 2, the React app:**

```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Vite forwards `/api/...` calls to the backend
(see `vite.config.ts`). Saving any `.tsx` file updates the page instantly
without losing state. That's hot module replacement, and it's most of why React
development feels fast.

**Offline / sample data:** before starting the API, run:

```powershell
$env:SPORTSDASH_FIXTURES="tests/fixtures"; $env:SPORTSDASH_TODAY="2026-10-02"
```

This serves made-up but ESPN-shaped responses from `backend/tests/fixtures/`.

**Checks:**

```powershell
cd backend;  python -m pytest -q          # 27 API + adapter tests
cd frontend; npm test                      # 68 tests: helpers + every page rendered with broken data
cd frontend; npm run build                 # type-check + production build
```

## Troubleshooting

- **Where errors show up.** Python errors and every ESPN request (`ESPN 200  212ms
  football/nfl/scoreboard?...`) print in the backend terminal. Vite's terminal only
  shows build problems. Errors inside React happen in the browser: press **F12** and
  open the **Console** tab.
- **A page shows "This page hit an error while rendering."** Click "Copy error
  details" and paste it somewhere useful. Navigating to another page recovers.
- **ESPN changed something.** Run the checks above, then compare the live feed with
  `backend/tests/fixtures/` (open the ESPN URL from the backend log in a browser).

## Pages

| URL | What's on it |
| --- | --- |
| `/` and `/?date=2026-10-03` | Day strip (two days back, five ahead). Your teams' games pinned at the top, then each league, live games first. Auto-refreshes while games can be live. |
| `/schedule?days=7&mine=1` | Next 3 / 7 / 14 days by day, with a "Your teams only" toggle. |
| `/standings?league=ncaaf` | Groups containing your teams first, with your rows highlighted. PGA shows the leaderboard. |
| `/teams` | Each team's next game with lines from every sportsbook, plus its full season. |
| `/game/nfl/401772001` | Scoreboard, linescore, win probability, team stats, scoring plays, player stats, game info, betting lines. |
| `/golf/pga/401703510` | Full leaderboard. |

The league chips in the header filter every page and are remembered in the browser.

## Learning React with this codebase

Read the frontend in this order. Each step introduces one or two ideas.

1. **`src/types.ts`**: TypeScript interfaces describing exactly what the API
   returns. Hover any variable in VS Code to see its type; misspell a field and
   the editor flags it before you run anything.
2. **`src/lib/format.ts`, `src/lib/games.ts`**: plain functions, no React. This
   is where logic belongs whenever possible, because it's easy to test (see
   `*.test.ts` next to them).
3. **`src/components/Logo.tsx`**: the smallest real component. It covers props
   (`src`, `abbr`, `size`), state (`useState`), and events (`onLoad`, `onError`).
   When state changes, React re-renders the component.
4. **`src/components/GameRow.tsx`**: composition. Components render other
   components (`<Logo>`, `<OddsLines>`), and JSX is just JavaScript, so
   `{cond && <X/>}` and `.map()` replace template `if`/`for`.
5. **`src/lib/settings.tsx`**: React context. This is shared state (config,
   enabled leagues) that any component reads with `useSettings()` instead of
   passing props down five levels. It also shows `useMemo` and `localStorage`.
6. **`src/lib/api.ts` + `src/pages/Scores.tsx`**: data fetching with
   **TanStack Query**. `useQuery(scoresQuery(date))` handles loading, errors,
   caching, background refresh (`refetchInterval`) and keeping the old day on
   screen while the new one loads (`placeholderData`). Hovering a day in the
   strip calls `prefetchQuery`, which is why clicks feel instant.
7. **`src/App.tsx`**: routing with **React Router**. `<Routes>` maps URLs to
   pages, `<Outlet>` is where the matched page renders, `<NavLink>` highlights
   the current section, and `useSearchParams`/`useParams` read the URL.
8. **`src/components/WinProbChart.tsx`**: an interactive chart in plain SVG with
   pointer events, no chart library.

Things to try:

- Add a "Yesterday's finals for your teams" strip at the top of Scores. It needs
  only `games.ts` helpers and one more `useQuery`.
- Show the spread result (covered / didn't cover) on finished games in
  `TeamsPage`. The data is already in `game.odds`.
- Install the React DevTools browser extension, open the Components tab, and
  watch which components re-render when you toggle a league chip.

Library versions: React 19, React Router 7, TanStack Query 5, Vite 8,
TypeScript 5.9. TypeScript 7 (the new native compiler) exists, but most
tutorials and tooling still target 5.x.

## Configure leagues and teams

Everything lives in `config.yaml`:

```yaml
leagues:
  - key: nhl                 # anything unique; used in URLs
    name: NHL
    sport: hockey            # ESPN sport slug
    league: nhl              # ESPN league slug
    standings_columns: [GP, W, L, OTL, PTS]

teams:
  - name: Washington Capitals
    short: WSH
    espn_id: "23"            # from the team's ESPN URL: espn.com/nhl/team/_/id/23
    leagues: [nhl]
    color: "#C8102E"
```

Any league ESPN publishes a scoreboard for works without code changes. Find the
slugs by opening `https://site.api.espn.com/apis/site/v2/sports/<sport>/<league>/scoreboard`.
Examples: `basketball/nba`, `baseball/mlb`, `soccer/usa.1` (MLS),
`soccer/uefa.champions`.

`params` adds query parameters to the scoreboard. College feeds need `groups`, or
ESPN returns only ranked games: `80` is all FBS football, `50` is all Division I
basketball.

`standings_columns` picks columns by ESPN's stat abbreviation. If none match, the
first ten stats ESPN returns are shown, so a wrong guess still works.

## How the backend works

```
backend/sportsdash/
  config.py        YAML -> typed config
  espn.py          HTTP client with TTL cache; serves stale data if ESPN errors
  adapters/
    parse.py       ESPN JSON -> models (handles scoreboard vs schedule vs summary shapes)
    team_sport.py  NFL / college / soccer: games, schedule, standings, game detail
    golf.py        PGA: calendar, current event, leaderboard
  models.py        dataclasses; the API returns these as JSON
  data.py          cross-league aggregation, fetched in parallel
  api.py           FastAPI routes + serves the built frontend
```

Caching: live days 30 s, future days 10 min, past days and standings 1 h.

## ESPN quirks

- **No date ranges.** Since September 2026 the scoreboard rejects
  `dates=YYYYMMDD-YYYYMMDD` with a 400. sportsdash makes one request per day
  (in parallel, each cached) and merges them.
- **`limit` is capped at 500.** Anything higher silently returns only 25 games.
- Betting lines appear only when ESPN publishes them, usually within a week of
  the game.
- College standings are empty until the season starts (NCAAB until November).
