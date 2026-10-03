// Pure helpers for working with games. No React here, so they're easy to unit test.

import type { Game, Odds, Team, TeamConfig } from "../types";

/** Is one of the configured teams playing in this game (in a league they're configured for)? */
export function isMyGame(game: Game, teams: TeamConfig[]): boolean {
  return teams.some(
    (t) => t.leagues.includes(game.league) && (t.espn_id === game.home.id || t.espn_id === game.away.id),
  );
}

export function isMyTeam(team: Pick<Team, "id">, league: string, teams: TeamConfig[]): boolean {
  return teams.some((t) => t.espn_id === team.id && t.leagues.includes(league));
}

const STATE_ORDER = { in: 0, pre: 1, post: 2 } as const;

/** Live first, then upcoming, then finished; by start time within each, then ranked matchups first. */
export function sortLiveFirst(games: Game[]): Game[] {
  return [...games].sort(
    (a, b) => STATE_ORDER[a.state] - STATE_ORDER[b.state] || byStart(a, b) || byRank(a, b),
  );
}

/** The better of the two teams' ranks (1 is best); Infinity when neither is ranked. */
export function bestRank(game: Game): number {
  return Math.min(game.home.rank || Infinity, game.away.rank || Infinity);
}

function byRank(a: Game, b: Game): number {
  const ra = bestRank(a);
  const rb = bestRank(b);
  return ra === rb ? 0 : ra < rb ? -1 : 1; // not ra - rb: Infinity - Infinity is NaN
}

export function isRanked(game: Game): boolean {
  return bestRank(game) !== Infinity;
}

export function byStart(a: { start: string | null }, b: { start: string | null }): number {
  if (a.start === b.start) return 0;
  if (!a.start) return 1;
  if (!b.start) return -1;
  return a.start < b.start ? -1 : 1; // ISO strings in UTC sort chronologically
}

/** Group items into a Map keyed by whatever `key` returns, preserving first-seen order. */
export function groupBy<T, K>(items: T[], key: (item: T) => K): Map<K, T[]> {
  const out = new Map<K, T[]>();
  for (const item of items) {
    const k = key(item);
    const list = out.get(k);
    if (list) list.push(item);
    else out.set(k, [item]);
  }
  return out;
}

export function location(g: { venue: string; city: string }): string {
  return [g.venue, g.city].filter(Boolean).join(", ");
}

/** Whether the game was postponed/canceled (ESPN reports these as "pre" with a status word). */
export function isOff(game: Game): boolean {
  return /^(postponed|canceled|cancelled|delayed|suspended)/i.test(game.detail);
}

/** From the perspective of `teamId`: opponent, home/away, and W/L when final. */
export function perspective(game: Game, teamId: string) {
  const home = game.home.id === teamId;
  const me = home ? game.home : game.away;
  const opp = home ? game.away : game.home;
  let won: boolean | null = null;
  if (game.state === "post") {
    if (me.winner || opp.winner) won = me.winner;
    else won = Number(me.score) > Number(opp.score);
  }
  return { home, me, opp, won };
}

export function hasLines(o: Odds | null | undefined): o is Odds {
  return !!o && !!(o.details || o.over_under != null || o.home_ml || o.away_ml);
}
