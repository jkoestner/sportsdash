"""Defensive parsers from ESPN JSON into sportsdash models.

ESPN's payloads vary by endpoint (scoreboard vs team schedule vs summary) and by
sport, so every accessor tolerates missing keys and both shapes where they differ.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..models import Game, Odds, Poll, PollEntry, StandingsGroup, StandingsRow, Team


def g(obj: Any, *path, default=None):
    """Safe nested get: g(d, "a", 0, "b")."""
    cur = obj
    for key in path:
        if isinstance(key, int):
            if not isinstance(cur, list) or len(cur) <= key:
                return default
            cur = cur[key]
        else:
            if not isinstance(cur, dict) or key not in cur:
                return default
            cur = cur[key]
    return default if cur is None else cur


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def score_text(score: Any) -> str:
    """Scoreboard gives "24"; team schedule gives {"value": 24.0, "displayValue": "24"}."""
    if isinstance(score, dict):
        return str(score.get("displayValue") or score.get("value") or "")
    return "" if score is None else str(score)


def fmt_ml(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        num = int(round(float(value)))
    except (TypeError, ValueError):
        return str(value)
    return f"+{num}" if num > 0 else str(num)


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_odds(raw: dict | None) -> Odds | None:
    """Works for scoreboard `competitions[].odds[]` and summary `pickcenter[]`."""
    if not raw:
        return None
    home_ml = g(raw, "homeTeamOdds", "moneyLine") or g(raw, "moneyline", "home", "close", "odds")
    away_ml = g(raw, "awayTeamOdds", "moneyLine") or g(raw, "moneyline", "away", "close", "odds")
    draw_ml = g(raw, "drawOdds", "moneyLine") or g(raw, "moneyline", "draw", "close", "odds")
    odds = Odds(
        provider=g(raw, "provider", "name", default=""),
        details=str(g(raw, "details", default="")),
        spread=_num(raw.get("spread")),
        over_under=_num(raw.get("overUnder")),
        home_ml=fmt_ml(home_ml),
        away_ml=fmt_ml(away_ml),
        draw_ml=fmt_ml(draw_ml),
    )
    return None if odds.empty else odds


def parse_team(comp: dict) -> Team:
    team = comp.get("team") or {}
    logo = team.get("logo") or g(team, "logos", 0, "href", default="")
    # Scoreboard: records[0].summary; schedule: record[0].displayValue; summary: record[0].summary
    record = (
        g(comp, "records", 0, "summary")
        or g(comp, "record", 0, "summary")
        or g(comp, "record", 0, "displayValue")
        or ""
    )
    rank = g(comp, "curatedRank", "current")
    rank = int(rank) if isinstance(rank, (int, float)) and 0 < rank < 99 else None
    return Team(
        id=str(team.get("id", "")),
        name=team.get("displayName") or team.get("name") or "",
        short=team.get("shortDisplayName") or team.get("name") or team.get("abbreviation") or "",
        abbr=team.get("abbreviation") or "",
        logo=logo or "",
        score=score_text(comp.get("score")),
        record=record,
        rank=rank,
        winner=bool(comp.get("winner")),
        home_away=comp.get("homeAway", ""),
        linescores=[
            str(ls.get("displayValue", ls.get("value", ""))) for ls in comp.get("linescores") or []
        ],
    )


def parse_status(status: dict) -> tuple[str, str]:
    t = status.get("type") or {}
    state = t.get("state") or "pre"
    detail = t.get("shortDetail") or t.get("detail") or t.get("description") or ""
    return state, detail


def _broadcasts(comp: dict) -> list[str]:
    names: list[str] = []
    for b in comp.get("broadcasts") or []:
        names.extend(b.get("names") or [])  # scoreboard shape
        short = g(b, "media", "shortName")  # schedule/summary shape
        if short:
            names.append(short)
    for b in comp.get("geoBroadcasts") or []:
        short = g(b, "media", "shortName")
        if short:
            names.append(short)
    seen: list[str] = []
    for n in names:
        if n and n not in seen:
            seen.append(n)
    return seen


def parse_competition(event: dict, comp: dict, league_key: str) -> Game | None:
    competitors = comp.get("competitors") or []
    if len(competitors) < 2:
        return None
    teams = [parse_team(c) for c in competitors]
    home = next((t for t in teams if t.home_away == "home"), teams[0])
    away = next((t for t in teams if t.home_away == "away"), teams[1])
    # The competition's status is the live one, but on the scoreboard it often omits the
    # readable text ("8:26 - 4th"); the event-level status has it.
    state, detail = parse_status(comp.get("status") or event.get("status") or {})
    if event.get("status"):
        _, event_detail = parse_status(event["status"])
        if event_detail and (not detail or detail in ("In Progress", "Scheduled", "Final")):
            detail = event_detail
    venue = comp.get("venue") or {}
    city = ", ".join(
        p for p in (g(venue, "address", "city"), g(venue, "address", "state") or g(venue, "address", "country")) if p
    )
    odds_list = comp.get("odds") or []
    note = g(comp, "notes", 0, "headline", default="")
    return Game(
        id=str(event.get("id") or comp.get("id") or ""),
        league=league_key,
        start=parse_date(comp.get("date") or event.get("date")),
        state=state,
        detail=detail,
        home=home,
        away=away,
        name=event.get("shortName") or event.get("name") or "",
        venue=venue.get("fullName") or "",
        city=city,
        neutral=bool(comp.get("neutralSite")),
        broadcasts=_broadcasts(comp),
        odds=parse_odds(odds_list[0]) if odds_list else None,
        time_valid=comp.get("timeValid", event.get("timeValid", True)) is not False,
        note=note,
    )


def parse_event(event: dict, league_key: str) -> Game | None:
    comp = g(event, "competitions", 0)
    if not comp:
        return None
    return parse_competition(event, comp, league_key)


def _stat_label(stat: dict) -> str:
    return stat.get("abbreviation") or stat.get("shortDisplayName") or stat.get("name") or ""


def _flatten_groups(node: dict, out: list[tuple[dict, str]], parent: str = "", depth: int = 0) -> None:
    """Standings nest league -> conference -> division -> standings.entries; collect leaf
    groups with the name of the group they sit in (never the league itself)."""
    if g(node, "standings", "entries"):
        out.append((node, parent))
    name = (node.get("name") or node.get("abbreviation") or "") if depth > 0 else ""
    for child in node.get("children") or []:
        _flatten_groups(child, out, name, depth + 1)


def parse_standings(data: dict, preferred_cols: list[str]) -> list[StandingsGroup]:
    leaves: list[tuple[dict, str]] = []
    _flatten_groups(data, leaves)
    groups: list[StandingsGroup] = []
    for node, parent in leaves:
        entries = g(node, "standings", "entries", default=[])
        # Decide columns from the first entry's stats.
        first_stats = entries[0].get("stats", []) if entries else []
        available = [_stat_label(s) for s in first_stats]
        cols = [c for c in preferred_cols if c in available]
        if not cols:
            cols = [c for c in available if c][:10]
        rows = []
        for e in entries:
            team = e.get("team") or {}
            stats = {}
            for s in e.get("stats") or []:
                label = _stat_label(s)
                if label and label not in stats:
                    stats[label] = str(s.get("displayValue", s.get("summary", s.get("value", ""))))
            rows.append(
                StandingsRow(
                    team_id=str(team.get("id", "")),
                    team=team.get("displayName") or team.get("name") or "",
                    abbr=team.get("abbreviation") or "",
                    logo=g(team, "logos", 0, "href", default=team.get("logo") or ""),
                    values=[stats.get(c, "") for c in cols],
                )
            )
        name = node.get("name") or node.get("abbreviation") or ""
        groups.append(StandingsGroup(name=name, columns=cols, rows=rows, parent=parent))
    return groups


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_poll(data: dict, poll_type: str) -> Poll | None:
    """One poll from the rankings endpoint, picked by its `type` ("ap", "usa", "cfp"...)."""
    raw = next((r for r in data.get("rankings") or [] if r.get("type") == poll_type), None)
    if not raw:
        return None
    entries = []
    for r in raw.get("ranks") or []:
        team = r.get("team") or {}
        rank = _int(r.get("current"))
        if not rank or not team.get("id"):
            continue
        previous = _int(r.get("previous"))
        entries.append(
            PollEntry(
                rank=rank,
                team_id=str(team["id"]),
                team=team.get("nickname") or team.get("location") or team.get("name") or "",
                abbr=team.get("abbreviation") or "",
                logo=team.get("logo") or g(team, "logos", 0, "href", default=""),
                record=r.get("recordSummary") or "",
                previous=previous if previous and previous > 0 else None,
                points=_int(r.get("points")),
                first_place_votes=_int(r.get("firstPlaceVotes")) or 0,
            )
        )
    return Poll(
        name=raw.get("name") or raw.get("shortName") or "",
        week=g(raw, "occurrence", "displayValue", default=""),
        date=parse_date(raw.get("date")),
        entries=sorted(entries, key=lambda e: e.rank),
    )
