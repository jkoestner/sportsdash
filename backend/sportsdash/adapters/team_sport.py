"""Adapter for head-to-head team sports (NFL, college football/basketball, soccer...)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

from .. import espn
from ..config import LeagueConfig
from ..models import Game, GameDetail, Odds, Play, PlayerTable, Playoffs, Poll, StandingsGroup
from .parse import g, parse_competition, parse_date, parse_event, parse_odds, parse_poll, parse_standings
from .playoffs import build_bracket, pad_bracket

SOCCER_EVENT_WORDS = ("goal", "card", "penalty")


# ESPN scoreboard quirks (changed Sept 2026):
#   * the `dates=YYYYMMDD-YYYYMMDD` range form now returns 400, so query one day at a time
#   * `limit` is capped at 500; anything higher silently falls back to 25 events
SCOREBOARD_LIMIT = 500
MAX_DAYS = 31
PLAYOFF_MAX_DAYS = 92  # NHL/NBA playoffs run about ten weeks; ESPN's windows add a few spare days

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
    def _scoreboard_data(self, day: date) -> dict:
        params = {**self.cfg.params, "dates": day.strftime("%Y%m%d"), "limit": SCOREBOARD_LIMIT}
        return self.client.get(f"{self.base}/scoreboard", params, ttl=_day_ttl(day))

    def scoreboard_day(self, day: date) -> list[Game]:
        data = self._scoreboard_data(day)
        return [gm for ev in data.get("events") or [] if (gm := parse_event(ev, self.cfg.key))]

    def games(self, start: date, end: date) -> list[Game]:
        """All games from start to end inclusive, one cached request per day."""
        n = min((end - start).days + 1, MAX_DAYS)
        days = [start + timedelta(days=i) for i in range(max(n, 0))]
        merged: dict[str, Game] = {}
        for day_games in _day_pool.map(self.scoreboard_day, days):
            for gm in day_games:
                merged[gm.id] = gm  # a game near midnight UTC can show on two days
        games = sorted(merged.values(), key=lambda gm: (gm.start is None, gm.start))
        return self.apply_poll(games)

    def _schedule_data(self, team_id: str) -> dict:
        return self.client.get(f"{self.base}/teams/{team_id}/schedule", ttl=espn.TTL_SCHEDULE)

    def team_schedule(self, team_id: str) -> list[Game]:
        data = self._schedule_data(team_id)
        games = [gm for ev in data.get("events") or [] if (gm := parse_event(ev, self.cfg.key))]
        return self.apply_poll(sorted(games, key=lambda gm: (gm.start is None, gm.start)))

    def team_info(self, team_id: str) -> dict:
        """ESPN's team block from the schedule feed: displayName, abbreviation, logo, color,
        standingSummary ("3rd in ACC")... Empty if ESPN doesn't know the team."""
        return self._schedule_data(team_id).get("team") or {}

    # ── rankings ────────────────────────────────────────────────────────────
    def poll(self) -> Poll | None:
        """The configured poll (e.g. AP Top 25), or None if the league has none."""
        if not self.cfg.rankings:
            return None
        data = self.client.get(f"{self.base}/rankings", ttl=espn.TTL_STANDINGS)
        return parse_poll(data, self.cfg.rankings)

    def apply_poll(self, games: list[Game]) -> list[Game]:
        """Use the configured poll's ranks instead of ESPN's curatedRank.

        curatedRank switches from AP to the CFP rankings once those come out in November.
        Only games after the poll was released are re-ranked: older games keep the rank
        each team had at the time.
        """
        poll = self.poll()
        if not poll or not poll.entries:
            return games  # poll unavailable: ESPN's own ranks are the best we have
        ranks = poll.ranks()
        for gm in games:
            if poll.date and gm.start and gm.start < poll.date:
                continue
            gm.home.rank = ranks.get(gm.home.id)
            gm.away.rank = ranks.get(gm.away.id)
        return games

    # ── playoffs ────────────────────────────────────────────────────────────
    def _postseason_window(self, year: int) -> tuple[datetime, datetime] | None:
        url = f"{espn.CORE}/{self.cfg.sport}/leagues/{self.cfg.league}/seasons/{year}/types/3"
        data = self.client.get(url, ttl=espn.TTL_STANDINGS)
        start, end = parse_date(data.get("startDate")), parse_date(data.get("endDate"))
        return (start, end) if start and end else None

    def playoffs(self, today: date) -> Playoffs | None:
        """This season's postseason bracket, or last season's if this one hasn't started.

        None when ESPN has no postseason for the league. The scoreboard can't be queried by
        date range or season type, so this fetches every day of the postseason (cached).
        """
        season = g(self._scoreboard_data(today), "leagues", 0, "season", "year")
        year = int(season) if season else today.year
        window = self._postseason_window(year)
        if window is None:
            return None
        next_start = None
        if window[0].date() > today:
            next_start = window[0]
            previous = self._postseason_window(year - 1)
            if previous is None:
                return Playoffs(league=self.cfg.key, season=year, start=window[0], end=window[1], next_start=next_start)
            year, window = year - 1, previous

        first = window[0].date()
        last = window[1].date()  # through the final: ESPN lists future games with TBD teams
        days = [first + timedelta(days=i) for i in range(min((last - first).days + 1, PLAYOFF_MAX_DAYS))]
        events: dict[str, dict] = {}
        for data in _day_pool.map(self._scoreboard_data, days):
            for ev in data.get("events") or []:
                if g(ev, "season", "type") == 3 and ev.get("id"):
                    events[str(ev["id"])] = ev
        stages, other = build_bracket(list(events.values()), self.cfg.key, self.cfg.playoffs_match)
        if next_start is None:  # this season's bracket: draw the rounds still to come
            stages = pad_bracket(stages, self.cfg.playoffs_rounds)
        return Playoffs(
            league=self.cfg.key, season=year, start=window[0], end=window[1],
            stages=stages, other=other, next_start=next_start,
        )

    # ── standings ───────────────────────────────────────────────────────────
    def standings(self) -> list[StandingsGroup]:
        url = f"{espn.V2}/{self.cfg.sport}/{self.cfg.league}/standings"
        # level=3 splits conferences into divisions (NFL, NHL, MLB...); leagues without
        # divisions come back unchanged.
        params = {"level": 3, **self.cfg.standings_params}
        data = self.client.get(url, params, ttl=espn.TTL_STANDINGS)
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
        self.apply_poll([game])

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
