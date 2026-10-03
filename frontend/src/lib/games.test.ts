import { describe, expect, it } from "vitest";
import type { Game, Team, TeamConfig } from "../types";
import { bestRank, groupBy, isMyGame, isOff, isRanked, perspective, sortLiveFirst } from "./games";

function team(id: string, extra: Partial<Team> = {}): Team {
  return { id, name: id, short: id, abbr: id, logo: "", score: "", record: "", rank: null, winner: false, home_away: "", linescores: [], ...extra };
}

function game(id: string, extra: Partial<Game> = {}): Game {
  return {
    id, league: "nfl", start: "2026-10-04T17:00:00Z", state: "pre", detail: "", home: team("6"), away: team("9"),
    name: "", venue: "", city: "", neutral: false, broadcasts: [], odds: null, time_valid: true, note: "", ...extra,
  };
}

const TEAMS: TeamConfig[] = [
  { name: "Virginia", short: "UVA", espn_id: "258", leagues: ["ncaaf", "ncaab"], color: "" },
  { name: "Cowboys", short: "DAL", espn_id: "6", leagues: ["nfl"], color: "" },
];

describe("isMyGame", () => {
  it("matches a configured team in a configured league", () => {
    expect(isMyGame(game("a"), TEAMS)).toBe(true);
  });
  it("ignores the same ESPN id in a different league", () => {
    // ESPN ids are only unique within a league; id 6 in college football isn't the Cowboys.
    expect(isMyGame(game("b", { league: "ncaaf" }), TEAMS)).toBe(false);
  });
});

describe("sortLiveFirst", () => {
  it("orders live, then upcoming, then final; by start time within each", () => {
    const games = [
      game("final", { state: "post", start: "2026-10-04T13:00:00Z" }),
      game("late", { start: "2026-10-04T20:00:00Z" }),
      game("live", { state: "in" }),
      game("early", { start: "2026-10-04T16:00:00Z" }),
      game("tbd", { start: null }),
    ];
    expect(sortLiveFirst(games).map((g) => g.id)).toEqual(["live", "early", "late", "tbd", "final"]);
  });
  it("puts ranked matchups first among games at the same time, best rank first", () => {
    const at = (id: string, home: number | null, away: number | null, start = "2026-10-03T16:00:00Z") =>
      game(id, { start, home: team("h", { rank: home }), away: team("a", { rank: away }) });
    const games = [
      at("unranked", null, null),
      at("no18", 18, null),
      at("earlier", null, null, "2026-10-03T12:00:00Z"),
      at("no3", null, 3),
      at("unranked2", null, null),
    ];
    // Time still wins: the earlier unranked game stays on top.
    expect(sortLiveFirst(games).map((g) => g.id)).toEqual(["earlier", "no3", "no18", "unranked", "unranked2"]);
  });
});

describe("bestRank / isRanked", () => {
  it("uses the better-ranked team and treats null as unranked", () => {
    const g = game("r", { home: team("h", { rank: 12 }), away: team("a", { rank: 5 }) });
    expect(bestRank(g)).toBe(5);
    expect(isRanked(g)).toBe(true);
    expect(isRanked(game("u"))).toBe(false);
  });
});

describe("perspective", () => {
  it("reports opponent, venue side and result from one team's view", () => {
    const g = game("x", { state: "post", home: team("21", { score: "20" }), away: team("6", { score: "27", winner: true }) });
    const p = perspective(g, "6");
    expect(p.home).toBe(false);
    expect(p.opp.id).toBe("21");
    expect(p.won).toBe(true);
  });
  it("falls back to comparing scores when ESPN omits the winner flag", () => {
    const g = game("y", { state: "post", home: team("6", { score: "17" }), away: team("9", { score: "24" }) });
    expect(perspective(g, "6").won).toBe(false);
  });
  it("has no result before the game ends", () => {
    expect(perspective(game("z"), "6").won).toBeNull();
  });
});

it("isOff spots postponed and canceled games", () => {
  expect(isOff(game("p", { detail: "Postponed" }))).toBe(true);
  expect(isOff(game("q", { detail: "Sun, October 4th at 1:00 PM EDT" }))).toBe(false);
});

it("groupBy keeps first-seen key order", () => {
  const out = groupBy(["epl", "nfl", "epl"], (x) => x);
  expect([...out.keys()]).toEqual(["epl", "nfl"]);
  expect(out.get("epl")).toHaveLength(2);
});
