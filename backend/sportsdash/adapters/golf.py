"""Adapter for golf (PGA Tour): tournaments rather than head-to-head games."""

from __future__ import annotations

from datetime import date, datetime, timezone

from .. import espn
from ..config import LeagueConfig
from ..models import GolfPlayer, Tournament
from .parse import g, parse_date, parse_status, score_text


def _overlaps(t_start: datetime | None, t_end: datetime | None, start: date, end: date) -> bool:
    if t_start is None:
        return False
    s = t_start.date()
    e = (t_end or t_start).date()
    return s <= end and e >= start


def _player(c: dict, state: str) -> GolfPlayer:
    lines = c.get("linescores") or []
    rounds = []
    for ls in lines:
        v = ls.get("value")
        if isinstance(v, (int, float)) and v > 0:
            rounds.append(str(int(v)))
    status = c.get("status") or {}
    thru = status.get("thru")
    thru_txt = ""
    if thru not in (None, ""):
        thru_txt = "F" if str(thru) == "18" else str(thru)
    if not thru_txt:
        thru_txt = g(status, "type", "shortDetail", default="") if state == "in" else ""
    today = g(lines[-1], "displayValue", default="") if lines and state == "in" else ""
    return GolfPlayer(
        pos=g(status, "position", "displayName", default="") or str(c.get("order", "")),
        name=g(c, "athlete", "displayName") or g(c, "team", "displayName") or g(c, "team", "name", default=""),
        score=score_text(c.get("score")) or "E",
        today=today,
        thru=thru_txt,
        rounds=rounds,
        flag=g(c, "athlete", "flag", "href", default=""),
    )


def _tournament(ev: dict, league_key: str) -> Tournament:
    status = ev.get("status") or g(ev, "competitions", 0, "status", default={})
    state, detail = parse_status(status)
    comp = g(ev, "competitions", 0, default={})
    venue = comp.get("venue") or g(ev, "courses", 0, default={}) or {}
    addr = venue.get("address") or {}
    players = [_player(c, state) for c in comp.get("competitors") or []]
    players.sort(key=lambda p: (int(p.pos.lstrip("T")) if p.pos.lstrip("T").isdigit() else 9999))
    return Tournament(
        id=str(ev.get("id", "")),
        league=league_key,
        name=ev.get("name") or ev.get("shortName") or "",
        start=parse_date(ev.get("date")),
        end=parse_date(ev.get("endDate")),
        state=state,
        detail=detail,
        venue=venue.get("fullName") or venue.get("name") or "",
        city=", ".join(p for p in (addr.get("city"), addr.get("state") or addr.get("country")) if p),
        players=players,
        purse=ev.get("displayPurse") or "",
    )


class GolfAdapter:
    def __init__(self, cfg: LeagueConfig, client: espn.EspnClient | None = None):
        self.cfg = cfg
        self._client = client

    @property
    def client(self) -> espn.EspnClient:
        return self._client or espn.client()

    @property
    def base(self) -> str:
        return f"{espn.SITE}/{self.cfg.sport}/{self.cfg.league}"

    def _scoreboard(self, day: date | None = None) -> dict:
        params = {"dates": day.strftime("%Y%m%d")} if day else {}
        return self.client.get(f"{self.base}/scoreboard", params, ttl=espn.TTL_LIVE)

    def current(self) -> list[Tournament]:
        """Tournament(s) in progress or the next one up."""
        data = self._scoreboard()
        return [_tournament(ev, self.cfg.key) for ev in data.get("events") or []]

    def calendar(self) -> list[Tournament]:
        data = self._scoreboard()
        cal = g(data, "leagues", 0, "calendar", default=[])
        out = []
        for item in cal:
            if not isinstance(item, dict):
                continue
            ev_id = item.get("id") or str(g(item, "event", "$ref", default="")).rstrip("/").split("/")[-1].split("?")[0]
            out.append(
                Tournament(
                    id=str(ev_id),
                    league=self.cfg.key,
                    name=item.get("label", ""),
                    start=parse_date(item.get("startDate")),
                    end=parse_date(item.get("endDate")),
                    state="pre",
                    detail="",
                )
            )
        # Merge live state for anything currently on the scoreboard.
        live = {t.id: t for t in self.current()}
        return [live.get(t.id, t) for t in out] or list(live.values())

    def tournaments(self, start: date, end: date) -> list[Tournament]:
        return [t for t in self.calendar() if _overlaps(t.start, t.end, start, end)]

    def leaderboard(self, event_id: str) -> Tournament | None:
        for t in self.current():
            if t.id == event_id:
                return t
        cal = {t.id: t for t in self.calendar()}
        target = cal.get(event_id)
        if target and target.start:
            day = target.start.astimezone(timezone.utc).date()
            for ev in self._scoreboard(day).get("events") or []:
                if str(ev.get("id")) == event_id:
                    return _tournament(ev, self.cfg.key)
        return target
