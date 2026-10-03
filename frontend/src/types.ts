// Shapes returned by the FastAPI backend (backend/sportsdash/models.py).
// Field names stay snake_case to match Python exactly; datetimes are ISO strings in UTC.

export type GameState = "pre" | "in" | "post";

export interface Team {
  id: string;
  name: string;
  short: string;
  abbr: string;
  logo: string;
  score: string;
  record: string;
  rank: number | null;
  winner: boolean;
  home_away: string;
  linescores: string[];
}

export interface Odds {
  provider: string;
  details: string; // "DAL -2.5"
  spread: number | null;
  over_under: number | null;
  home_ml: string;
  away_ml: string;
  draw_ml: string; // soccer only
}

export interface Game {
  id: string;
  league: string;
  start: string | null;
  state: GameState;
  detail: string; // "Final", "Q3 4:12", "Sat, October 3rd at 3:30 PM EDT"
  home: Team;
  away: Team;
  name: string;
  venue: string;
  city: string;
  neutral: boolean;
  broadcasts: string[];
  odds: Odds | null;
  time_valid: boolean;
  note: string;
}

export interface GolfPlayer {
  pos: string;
  name: string;
  score: string;
  today: string;
  thru: string;
  rounds: string[];
  flag: string;
}

export interface Tournament {
  id: string;
  league: string;
  name: string;
  start: string | null;
  end: string | null;
  state: GameState;
  detail: string;
  venue: string;
  city: string;
  players: GolfPlayer[];
  purse: string;
}

export interface StandingsRow {
  team_id: string;
  team: string;
  abbr: string;
  logo: string;
  values: string[];
}

export interface StandingsGroup {
  name: string;
  columns: string[];
  rows: StandingsRow[];
}

export interface PlayerTable {
  team: string;
  title: string;
  labels: string[];
  rows: string[][]; // first cell is the player's name
  totals: string[];
}

export interface Play {
  period: string;
  clock: string;
  team: string;
  text: string;
  score: string;
}

export interface GameDetail {
  game: Game;
  team_stats: [label: string, away: string, home: string][];
  player_tables: PlayerTable[];
  plays: Play[];
  odds: Odds[];
  attendance: string;
  weather: string;
  win_prob: number[]; // home win %, 0-100, one per play
  officials: string[];
}

export interface LeagueInfo {
  key: string;
  name: string;
  sport: string;
  kind: "team" | "golf";
}

export interface TeamConfig {
  name: string;
  short: string;
  espn_id: string;
  leagues: string[];
  color: string;
}

export interface AppConfig {
  today: string; // YYYY-MM-DD in the configured timezone
  timezone: string;
  refresh_seconds: number;
  schedule_days: number;
  leagues: LeagueInfo[];
  teams: TeamConfig[];
}

export interface ScoresResponse {
  date: string;
  games: Game[];
  tournaments: Tournament[];
}

export interface ScheduleResponse {
  start: string;
  end: string;
  games: Game[];
  tournaments: Tournament[];
}

export interface StandingsResponse {
  league: string;
  groups: StandingsGroup[];
  tournaments: Tournament[];
}

export interface TeamPanel {
  team: TeamConfig;
  league: LeagueInfo & { league: string };
  games: Game[];
  next_game: Game | null;
  next_odds: Odds[];
  record: string;
}
