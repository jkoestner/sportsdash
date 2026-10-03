"""Adapter tests against ESPN-shaped fixtures (no network)."""

from __future__ import annotations

from datetime import date

from conftest import CFG
from sportsdash.adapters import adapter_for
from sportsdash.adapters.parse import fmt_ml, parse_odds, score_text
from sportsdash.adapters.team_sport import SCOREBOARD_LIMIT, TeamSportAdapter
from sportsdash.espn import fixture_key

WEEK = (date(2026, 10, 2), date(2026, 10, 9))


def test_fixture_key():
    assert fixture_key("https://x/apis/site/v2/sports/football/nfl/summary", {"event": "1"}) == "football__nfl__summary__1.json"
    assert fixture_key("https://x/apis/v2/sports/soccer/eng.1/standings", None) == "soccer__eng.1__standings.json"


class RecordingClient:
    """Stands in for EspnClient and records every request."""

    def __init__(self):
        self.calls: list[dict] = []

    def get(self, url, params=None, ttl=0):
        self.calls.append(dict(params or {}))
        day = params["dates"]
        return {"events": [{
            "id": f"ev{day}", "date": f"{day[:4]}-{day[4:6]}-{day[6:]}T18:00Z",
            "competitions": [{"competitors": [
                {"homeAway": "home", "team": {"id": "1", "abbreviation": "H"}},
                {"homeAway": "away", "team": {"id": "2", "abbreviation": "A"}},
            ]}],
        }]}


def test_scoreboard_never_uses_date_ranges_or_big_limits():
    # Regression: ESPN returns 400 for dates=START-END and caps limit at 500 (Sept 2026).
    client = RecordingClient()
    adapter = TeamSportAdapter(CFG.league("ncaaf"), client=client)  # type: ignore[arg-type]
    games = adapter.games(date(2026, 10, 1), date(2026, 10, 3))
    assert sorted(c["dates"] for c in client.calls) == ["20261001", "20261002", "20261003"]
    assert all("-" not in c["dates"] for c in client.calls)
    assert all(c["limit"] <= SCOREBOARD_LIMIT for c in client.calls)
    assert all(c["groups"] == 80 for c in client.calls)  # league params still passed through
    assert [g.id for g in games] == ["ev20261001", "ev20261002", "ev20261003"]


def test_overlapping_days_are_deduplicated():
    games = adapter_for(CFG.league("nfl")).games(*WEEK)  # fixtures return the same events every day
    assert len(games) == len({g.id for g in games})


def test_odds_parsing_both_shapes():
    old = parse_odds({"details": "DAL -3", "overUnder": 49.5, "homeTeamOdds": {"moneyLine": -150}, "awayTeamOdds": {"moneyLine": 130}})
    assert (old.details, old.over_under, old.home_ml, old.away_ml) == ("DAL -3", 49.5, "-150", "+130")
    new = parse_odds({"moneyline": {"home": {"close": {"odds": "+110"}}, "away": {"close": {"odds": "-130"}}}})
    assert (new.home_ml, new.away_ml) == ("+110", "-130")
    assert parse_odds({}) is None
    assert fmt_ml("EVEN") == "EVEN"


def test_score_shapes():
    assert score_text("24") == "24"
    assert score_text({"value": 24.0, "displayValue": "24"}) == "24"
    assert score_text(None) == ""


def test_nfl_games_have_location_time_odds():
    games = adapter_for(CFG.league("nfl")).games(*WEEK)
    dal = next(gm for gm in games if gm.home.abbr == "DAL")
    assert dal.start is not None and dal.state == "pre"
    assert dal.location == "AT&T Stadium, Arlington, TX"
    assert dal.broadcasts == ["CBS"]
    assert dal.odds.details == "DAL -2.5" and dal.odds.over_under == 49.5


def test_soccer_three_way_moneyline():
    live = next(gm for gm in adapter_for(CFG.league("epl")).games(*WEEK) if gm.state == "in")
    assert live.odds.draw_ml == "+240"
    assert live.home.score == "1"


def test_standings_columns_and_groups():
    nfl = adapter_for(CFG.league("nfl")).standings()
    assert nfl[0].columns[:3] == ["W", "L", "T"]
    cfb = adapter_for(CFG.league("ncaaf")).standings()
    acc = next(grp for grp in cfb if "Atlantic" in grp.name)
    assert acc.has_team({"258"})
    assert adapter_for(CFG.league("ncaab")).standings() == []


def test_game_detail():
    d = adapter_for(CFG.league("nfl")).detail("401772001")
    assert d.game.away.linescores == ["3", "14", "0", "10"]
    assert ("Total Yards", "384", "321") in d.team_stats
    assert d.plays[0].team == "PHI" and d.plays[0].period == "Q1"
    assert d.player_tables and d.win_prob and d.attendance == "69,879"


def test_team_schedule_and_record():
    from sportsdash.data import team_panels

    panels = {(p.team.short, p.league.key): p for p in team_panels(CFG)}
    dal = panels[("DAL", "nfl")]
    assert dal.record == "3-1"
    assert dal.next_game.id == "401772045"
    assert len(dal.next_odds) == 2
    assert panels[("UVA", "ncaaf")].record == "2-1"


def test_golf():
    golf = adapter_for(CFG.league("pga"))
    t = golf.leaderboard("401703510")
    assert t.players[0].name == "Ben Griffin" and t.players[0].thru == "14"
    names = [x.name for x in golf.tournaments(date(2026, 10, 1), date(2026, 10, 12))]
    assert names == ["Sanderson Farms Championship", "Baycurrent Classic"]


def test_real_shapes_status_text_and_team_golf():
    """Shapes seen in live ESPN data (Oct 2026) that the original fixtures didn't cover."""
    from sportsdash.adapters.golf import _tournament
    from sportsdash.adapters.parse import parse_event

    # Scoreboard: competition status lacks shortDetail; the event status has it.
    ev = {
        "id": "401858476", "date": "2026-10-03T00:00Z",
        "status": {"type": {"state": "in", "description": "In Progress", "shortDetail": "8:26 - 4th"}},
        "competitions": [{
            "status": {"type": {"state": "in", "description": "In Progress"}},
            "venue": {"fullName": None, "address": {"city": "Evanston", "state": "IL"}},
            "competitors": [
                {"homeAway": "home", "score": "31", "team": {"id": "77", "abbreviation": "NU"}},
                {"homeAway": "away", "score": "24", "team": {"id": "1", "abbreviation": None}},
            ],
        }],
    }
    gm = parse_event(ev, "ncaaf")
    assert gm.detail == "8:26 - 4th" and gm.state == "in"
    assert gm.venue == "" and gm.away.abbr == ""  # explicit nulls become empty strings

    # Team match play (Presidents Cup / Ryder Cup): competitors are teams, not athletes.
    cup = {
        "id": "401824815", "name": "Presidents Cup", "date": "2026-09-24T04:00Z", "endDate": "2026-09-27T04:00Z",
        "status": {"type": {"state": "in", "description": "In Progress"}},
        "competitions": [{"competitors": [
            {"order": 1, "type": "team", "score": "3", "team": {"displayName": "USA"}},
            {"order": 2, "type": "team", "score": "2", "team": {"displayName": "International", "name": "INTL"}},
        ]}],
    }
    t = _tournament(cup, "pga")
    assert [p.name for p in t.players] == ["USA", "International"]
    assert [p.score for p in t.players] == ["3", "2"]
