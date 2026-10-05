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
    parent: str = ""  # conference, when this group is a division inside one

    def has_team(self, team_ids: set[str]) -> bool:
        return any(r.team_id in team_ids for r in self.rows)


@dataclass
class PollEntry:
    rank: int
    team_id: str
    team: str
    abbr: str
    logo: str
    record: str = ""
    previous: int | None = None  # last week's rank; None if unranked
    points: int | None = None
    first_place_votes: int = 0


@dataclass
class Poll:
    name: str  # "AP Top 25"
    week: str  # "Week 5"
    date: datetime | None
    entries: list[PollEntry] = field(default_factory=list)

    def ranks(self) -> dict[str, int]:
        return {e.team_id: e.rank for e in self.entries}


@dataclass
class SeriesTeam:
    id: str
    name: str
    short: str
    abbr: str
    logo: str
    rank: int | None = None  # poll rank (college); pro leagues have none
    wins: int = 0
    winner: bool = False


@dataclass
class PlayoffSeries:
    """One matchup in a round: a best-of-N series, or a single game (best_of 1)."""
    round: str  # "ALDS", "AFC Wild Card", "East 1st Round"
    best_of: int
    teams: list[SeriesTeam]
    summary: str = ""  # "LAD lead series 2-1"
    completed: bool = False
    games: list[Game] = field(default_factory=list)


@dataclass
class PlayoffStage:
    """A bracket column: every series played at the same stage, e.g. both Division Series."""
    name: str  # "Division Series", "Wild Card", "1st Round"
    series: list[PlayoffSeries] = field(default_factory=list)


@dataclass
class Playoffs:
    league: str
    season: int  # ESPN's season year, e.g. 2026 (NHL 2026 = the 2025-26 season)
    start: datetime | None
    end: datetime | None
    stages: list[PlayoffStage] = field(default_factory=list)
    other: list[Game] = field(default_factory=list)  # postseason games outside the bracket (bowls)
    next_start: datetime | None = None  # set when this season's playoffs haven't begun


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
class Situation:
    """Live football state: who has the ball, where, and the down."""
    possession: str = ""  # team id with the ball
    down_distance: str = ""  # "3rd & 16 at MIN 42"
    short_down_distance: str = ""  # "3rd & 16"
    yards_to_endzone: int | None = None  # for the team with the ball
    distance: int | None = None  # yards to go for a first down
    red_zone: bool = False
    drive: str = ""  # "6 plays, 48 yards, 3:12"
    last_play: str = ""


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
    situation: Situation | None = None  # live football games only
