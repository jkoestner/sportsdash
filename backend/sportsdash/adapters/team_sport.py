"""Adapter for head-to-head team sports (NFL, college football/basketball, soccer...)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from .. import espn
from ..config import LeagueConfig
from ..models import Game, GameDetail, Odds, Play, PlayerTable, StandingsGroup
from .parse import g, parse_competition, parse_event, parse_odds, parse_standings

SOCCER_EVENT_WORDS = ("goal", "card", "penalty")


# ESPN scoreboard quirks (changed Sept 2026):
#   * the `dates=YYYYMMDD-YYYYMMDD` range form now returns 400, so query one day at a time
#   * `limit` is capped at 500; anything higher silently falls back to 25 events
SCOREBOARD_LIMIT = 500
MAX_DAYS = 31

# Separate pool from data.py's so per-day fetches never wait behind league fetches.
_day_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="espn-day")


def _day_ttl(day: date) -> int:
    today = date.today()
    if today - timedelta(days=1) <= day <= today:
        return espn.TTL_LIVE  # games may be in progress (or just ended late last night)
    if day < today:
        return espn.TTL_STANDINGS  # finished days barely change
    return espn.TTL_SCHEDULE


class TeamSportAdapter:
    def __init__(self, cfg: LeagueConfig, client: espn.EspnClient | None = None):
        self.cfg = cfg
        self._client = client

    @property
    def client(self) -> espn.EspnClient:
        return self._client or espn.client()

    @property
    def base(self) -> str:
        return f"{espn.SITE}/{self.cfg.sport}/{self.cfg.league}"

    # ── scores / schedule ───────────────────────────────────────────────────
    def scoreboard_day(self, day: date) -> list[Game]:
        params = {**self.cfg.params, "dates": day.strftime("%Y%m%d"), "limit": SCOREBOARD_LIMIT}
        data = self.client.get(f"{self.base}/scoreboard", params, ttl=_day_ttl(day))
        return [gm for ev in data.get("events") or [] if (gm := parse_event(ev, self.cfg.key))]

    def games(self, start: date, end: date) -> list[Game]:
        """All games from start to end inclusive, one cached request per day."""
        n = min((end - start).days + 1, MAX_DAYS)
        days = [start + timedelta(days=i) for i in range(max(n, 0))]
        merged: dict[str, Game] = {}
        for day_games in _day_pool.map(self.scoreboard_day, days):
            for gm in day_games:
                merged[gm.id] = gm  # a game near midnight UTC can show on two days
        return sorted(merged.values(), key=lambda gm: (gm.start is None, gm.start))

    def team_schedule(self, team_id: str) -> list[Game]:
        data = self.client.get(f"{self.base}/teams/{team_id}/schedule", ttl=espn.TTL_SCHEDULE)
        games = [gm for ev in data.get("events") or [] if (gm := parse_event(ev, self.cfg.key))]
        return sorted(games, key=lambda gm: (gm.start is None, gm.start))

    # ── standings ───────────────────────────────────────────────────────────
    def standings(self) -> list[StandingsGroup]:
        url = f"{espn.V2}/{self.cfg.sport}/{self.cfg.league}/standings"
        data = self.client.get(url, ttl=espn.TTL_STANDINGS)
        return parse_standings(data, self.cfg.standings_columns)

    # ── game detail ─────────────────────────────────────────────────────────
    def summary_odds(self, event_id: str) -> list[Odds]:
        data = self.client.get(f"{self.base}/summary", {"event": event_id}, ttl=espn.TTL_SCHEDULE)
        return _summary_odds(data)

    def detail(self, event_id: str) -> GameDetail | None:
        data = self.client.get(f"{self.base}/summary", {"event": event_id}, ttl=espn.TTL_LIVE)
        comp = g(data, "header", "competitions", 0)
        if not comp:
            return None
        game = parse_competition({"id": g(data, "header", "id", default=event_id)}, comp, self.cfg.key)
        if game is None:
            return None

        info = data.get("gameInfo") or {}
        venue = info.get("venue") or {}
        if venue:
            game.venue = venue.get("fullName") or game.venue
            addr = venue.get("address") or {}
            game.city = ", ".join(p for p in (addr.get("city"), addr.get("state") or addr.get("country")) if p) or game.city

        detail = GameDetail(game=game)
        detail.odds = _summary_odds(data)
        if detail.odds and not game.odds:
            game.odds = detail.odds[0]
        if info.get("attendance"):
            detail.attendance = f"{int(info['attendance']):,}"
        weather = info.get("weather") or {}
        if weather:
            temp = weather.get("temperature")
            detail.weather = ", ".join(
                p for p in (f"{temp}°F" if temp is not None else "", weather.get("displayValue", "")) if p
            )
        detail.officials = [o.get("displayName", "") for o in info.get("officials") or [] if o.get("displayName")]

        detail.team_stats = _team_stats(data, game.home.id)
        detail.player_tables = _player_tables(data)
        detail.plays = _plays(data, game, self.cfg.sport)
        detail.win_prob = [
            round(float(p["homeWinPercentage"]) * 100, 1)
            for p in data.get("winprobability") or []
            if p.get("homeWinPercentage") is not None
        ]
        return detail


def _summary_odds(data: dict) -> list[Odds]:
    out: list[Odds] = []
    seen: set[str] = set()
    for raw in (data.get("pickcenter") or []) + (data.get("odds") or []):
        odds = parse_odds(raw)
        if odds and odds.provider not in seen:
            seen.add(odds.provider)
            out.append(odds)
    return out


def _team_stats(data: dict, home_id: str) -> list[tuple[str, str, str]]:
    teams = g(data, "boxscore", "teams", default=[])
    if len(teams) < 2:
        return []
    values: dict[str, dict[str, str]] = {"home": {}, "away": {}}
    order: list[str] = []
    for t in teams:
        side = "home" if str(g(t, "team", "id", default="")) == home_id else "away"
        for s in t.get("statistics") or []:
            label = s.get("label") or s.get("name")
            if not label:
                continue
            values[side][label] = s.get("displayValue", "")
            if label not in order:
                order.append(label)
    return [(label, values["away"].get(label, ""), values["home"].get(label, "")) for label in order]


def _player_tables(data: dict) -> list[PlayerTable]:
    tables: list[PlayerTable] = []
    for team_block in g(data, "boxscore", "players", default=[]):
        team = g(team_block, "team", "abbreviation") or g(team_block, "team", "displayName", default="")
        for grp in team_block.get("statistics") or []:
            labels = grp.get("labels") or []
            rows = []
            for a in grp.get("athletes") or []:
                stats = a.get("stats") or []
                if not stats or a.get("didNotPlay"):
                    continue
                rows.append([g(a, "athlete", "shortName") or g(a, "athlete", "displayName", default="")] + stats)
            if rows and labels:
                title = grp.get("text") or (grp.get("name") or "").replace("_", " ").title() or "Players"
                tables.append(PlayerTable(team=team, title=title, labels=labels, rows=rows, totals=grp.get("totals") or []))
    return tables


def _period_label(sport: str, number) -> str:
    if number in (None, ""):
        return ""
    n = int(number)
    if sport == "football":
        return f"Q{n}" if n <= 4 else ("OT" if n == 5 else f"{n - 4}OT")
    if sport == "basketball":
        return f"{n}H" if n <= 2 else ("OT" if n == 3 else f"{n - 2}OT")
    return f"P{n}"


def _plays(data: dict, game, sport: str) -> list[Play]:
    abbr = {game.home.id: game.home.abbr, game.away.id: game.away.abbr}
    plays: list[Play] = []
    if sport == "soccer":
        for ev in data.get("keyEvents") or []:
            kind = (g(ev, "type", "text", default="") or "").lower()
            if not (ev.get("scoringPlay") or any(w in kind for w in SOCCER_EVENT_WORDS)):
                continue
            plays.append(
                Play(
                    period="",
                    clock=g(ev, "clock", "displayValue", default=""),
                    team=g(ev, "team", "displayName", default=""),
                    text=ev.get("text") or g(ev, "type", "text", default=""),
                )
            )
        return plays
    for p in data.get("scoringPlays") or []:
        team_id = str(g(p, "team", "id", default=""))
        plays.append(
            Play(
                period=_period_label(sport, g(p, "period", "number")),
                clock=g(p, "clock", "displayValue", default=""),
                team=g(p, "team", "abbreviation") or abbr.get(team_id, ""),
                text=p.get("text", ""),
                score=(
                    f"{p['awayScore']}-{p['homeScore']}"
                    if p.get("awayScore") is not None and p.get("homeScore") is not None
                    else ""
                ),
            )
        )
    return plays
