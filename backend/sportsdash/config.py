"""Load the YAML config into typed objects."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

_HERE = Path(__file__).resolve().parent
# Repo layout: <root>/config.yaml next to backend/ and frontend/
DEFAULT_PATH = next(
    (p for p in (_HERE.parent.parent / "config.yaml", _HERE.parent / "config.yaml") if p.exists()),
    _HERE.parent.parent / "config.yaml",
)


@dataclass
class LeagueConfig:
    key: str
    name: str
    sport: str
    league: str
    kind: str = "team"  # "team" or "golf"
    params: dict = field(default_factory=dict)
    standings_columns: list[str] = field(default_factory=list)

    @property
    def is_golf(self) -> bool:
        return self.kind == "golf"


@dataclass
class TeamConfig:
    name: str
    short: str
    espn_id: str
    leagues: list[str]
    color: str = "#888888"


@dataclass
class AppConfig:
    timezone: str
    refresh_seconds: int
    schedule_days: int
    leagues: list[LeagueConfig]
    teams: list[TeamConfig]

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def league(self, key: str) -> LeagueConfig:
        for lg in self.leagues:
            if lg.key == key:
                return lg
        raise KeyError(f"Unknown league '{key}'")

    def team_ids(self) -> set[str]:
        return {t.espn_id for t in self.teams}

    def team_for(self, team_id: str, league_key: str) -> TeamConfig | None:
        for t in self.teams:
            if t.espn_id == str(team_id) and league_key in t.leagues:
                return t
        return None


def load_config(path: str | os.PathLike | None = None) -> AppConfig:
    path = Path(path or os.environ.get("SPORTSDASH_CONFIG") or DEFAULT_PATH)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    leagues = [LeagueConfig(**lg) for lg in raw.get("leagues", [])]
    teams = [
        TeamConfig(**{**t, "espn_id": str(t["espn_id"])}) for t in raw.get("teams", [])
    ]
    return AppConfig(
        timezone=raw.get("timezone", "America/New_York"),
        refresh_seconds=int(raw.get("refresh_seconds", 60)),
        schedule_days=int(raw.get("schedule_days", 7)),
        leagues=leagues,
        teams=teams,
    )
