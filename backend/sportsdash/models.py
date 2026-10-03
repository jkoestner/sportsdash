"""Normalized data shapes shared by every league adapter and the UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Team:
    id: str
    name: str
    short: str
    abbr: str
    logo: str = ""
    score: str = ""
    record: str = ""
    rank: int | None = None
    winner: bool = False
    home_away: str = ""
    linescores: list[str] = field(default_factory=list)


@dataclass
class Odds:
    provider: str = ""
    details: str = ""  # e.g. "DAL -3.5"
    spread: float | None = None
    over_under: float | None = None
    home_ml: str = ""
    away_ml: str = ""
    draw_ml: str = ""  # soccer only

    @property
    def empty(self) -> bool:
        return not (self.details or self.over_under or self.home_ml or self.away_ml)


@dataclass
class Game:
    id: str
    league: str
    start: datetime | None  # timezone-aware UTC
    state: str  # "pre" | "in" | "post"
    detail: str  # "Sun, Oct 4th at 1:00 PM EDT", "Q3 4:12", "Final"
    home: Team
    away: Team
    name: str = ""
    venue: str = ""
    city: str = ""
    neutral: bool = False
    broadcasts: list[str] = field(default_factory=list)
    odds: Odds | None = None
    time_valid: bool = True
    note: str = ""  # e.g. bowl name, matchday headline

    def involves(self, team_ids: set[str]) -> bool:
        return self.home.id in team_ids or self.away.id in team_ids

    @property
    def location(self) -> str:
        return ", ".join(p for p in (self.venue, self.city) if p)


@dataclass
class GolfPlayer:
    pos: str
    name: str
    score: str  # to par
    today: str = ""
    thru: str = ""
    rounds: list[str] = field(default_factory=list)
    flag: str = ""


@dataclass
class Tournament:
    id: str
    league: str
    name: str
    start: datetime | None
    end: datetime | None
    state: str
    detail: str
    venue: str = ""
    city: str = ""
    players: list[GolfPlayer] = field(default_factory=list)
    purse: str = ""

    @property
    def location(self) -> str:
        return ", ".join(p for p in (self.venue, self.city) if p)


@dataclass
class StandingsRow:
    team_id: str
    team: str
    abbr: str
    logo: str
    values: list[str]


@dataclass
class StandingsGroup:
    name: str
    columns: list[str]
    rows: list[StandingsRow]

    def has_team(self, team_ids: set[str]) -> bool:
        return any(r.team_id in team_ids for r in self.rows)


@dataclass
class PlayerTable:
    team: str
    title: str
    labels: list[str]
    rows: list[list[str]]  # first cell is player name
    totals: list[str] = field(default_factory=list)


@dataclass
class Play:
    period: str
    clock: str
    team: str
    text: str
    score: str = ""


@dataclass
class GameDetail:
    game: Game
    team_stats: list[tuple[str, str, str]] = field(default_factory=list)  # label, away, home
    player_tables: list[PlayerTable] = field(default_factory=list)
    plays: list[Play] = field(default_factory=list)
    odds: list[Odds] = field(default_factory=list)
    attendance: str = ""
    weather: str = ""
    win_prob: list[float] = field(default_factory=list)  # home win %, 0-100, per play
    officials: list[str] = field(default_factory=list)
