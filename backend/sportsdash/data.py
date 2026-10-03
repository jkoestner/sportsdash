"""Aggregate data across configured leagues for the pages (fetches run in parallel)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .adapters import adapter_for
from .config import AppConfig, LeagueConfig, TeamConfig
from .models import Game, Odds, StandingsGroup, Tournament

_pool = ThreadPoolExecutor(max_workers=8)


def local_day(dt: datetime | None, cfg: AppConfig) -> date | None:
    return dt.astimezone(cfg.tz).date() if dt else None


def _active(cfg: AppConfig, keys: list[str] | None) -> list[LeagueConfig]:
    return [lg for lg in cfg.leagues if keys is None or lg.key in keys]


def games_between(cfg: AppConfig, start: date, end: date, keys: list[str] | None = None) -> dict[str, list[Game]]:
    """Games per league whose local start date falls in [start, end]."""
    leagues = [lg for lg in _active(cfg, keys) if not lg.is_golf]
    # Query one extra UTC day each side so late-night local games aren't dropped.
    futures = {
        lg.key: _pool.submit(adapter_for(lg).games, start - timedelta(days=1), end + timedelta(days=1))
        for lg in leagues
    }
    out: dict[str, list[Game]] = {}
    for key, fut in futures.items():
        games = fut.result()
        out[key] = [gm for gm in games if (d := local_day(gm.start, cfg)) and start <= d <= end]
    return out


def tournaments_between(cfg: AppConfig, start: date, end: date, keys: list[str] | None = None) -> dict[str, list[Tournament]]:
    leagues = [lg for lg in _active(cfg, keys) if lg.is_golf]
    futures = {lg.key: _pool.submit(adapter_for(lg).tournaments, start, end) for lg in leagues}
    return {k: f.result() for k, f in futures.items()}


def standings(cfg: AppConfig, league_key: str) -> list[StandingsGroup]:
    lg = cfg.league(league_key)
    if lg.is_golf:
        return []
    groups = adapter_for(lg).standings()
    fav = cfg.team_ids()
    # Groups containing one of your teams first.
    return sorted(groups, key=lambda grp: not grp.has_team(fav))


@dataclass
class TeamPanel:
    team: TeamConfig
    league: LeagueConfig
    games: list[Game] = field(default_factory=list)
    next_game: Game | None = None
    next_odds: list[Odds] = field(default_factory=list)
    record: str = ""


def _team_panel(cfg: AppConfig, team: TeamConfig, lg: LeagueConfig) -> TeamPanel:
    adapter = adapter_for(lg)
    games = adapter.team_schedule(team.espn_id)  # type: ignore[union-attr]
    panel = TeamPanel(team=team, league=lg, games=games)
    upcoming = [gm for gm in games if gm.state != "post"]
    if upcoming:
        panel.next_game = upcoming[0]
        panel.next_odds = adapter.summary_odds(upcoming[0].id)  # type: ignore[union-attr]
    finals = [gm for gm in games if gm.state == "post"]
    if finals:
        wins = sum(1 for gm in finals if _won(gm, team.espn_id))
        panel.record = f"{wins}-{len(finals) - wins}"
    return panel


def _won(gm: Game, team_id: str) -> bool:
    me = gm.home if gm.home.id == team_id else gm.away
    other = gm.away if me is gm.home else gm.home
    if me.winner or other.winner:
        return me.winner
    try:
        return float(me.score) > float(other.score)
    except ValueError:
        return False


def team_panels(cfg: AppConfig, keys: list[str] | None = None) -> list[TeamPanel]:
    jobs = []
    for team in cfg.teams:
        for key in team.leagues:
            lg = cfg.league(key)
            if keys is None or key in keys:
                jobs.append(_pool.submit(_team_panel, cfg, team, lg))
    return [j.result() for j in jobs]
