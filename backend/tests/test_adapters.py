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
        if not url.endswith("/scoreboard"):
            return {}  # e.g. the rankings feed: no poll, so ESPN's ranks are kept
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


def test_poll_reranks_only_games_after_its_release():
    from sportsdash.adapters.parse import parse_poll

    adapter = adapter_for(CFG.league("ncaaf"))
    poll = adapter.poll()
    assert poll.ranks()["2390"] == 10
    sched = adapter.team_schedule("61")
    before, after = sched  # Sept 19 final, Oct 3 game; poll released Sept 27
    assert before.home.rank is None  # kept the scoreboard's rank at the time (none in the fixture)
    assert (after.home.rank, after.away.rank) == (4, 2)
    assert adapter_for(CFG.league("nfl")).poll() is None
    assert parse_poll({"rankings": [{"type": "usa", "ranks": []}]}, "ap") is None
    assert parse_poll({}, "ap") is None


def test_playoff_round_and_stage_names():
    from sportsdash.adapters.playoffs import round_name, stage_name

    assert round_name("ALDS - Game 2") == "ALDS"
    assert round_name("AFC Wild Card Playoffs") == "AFC Wild Card"
    cfp = "College Football Playoff"
    assert round_name("College Football Playoff Quarterfinal at the Rose Bowl Presented by Prudential", cfp) == "Quarterfinal"
    assert round_name("College Football Playoff First Round Game", cfp) == "First Round"
    ncaa = "NCAA Men's Basketball Championship"
    assert round_name("NCAA Men's Basketball Championship - South Region - Sweet 16", ncaa) == "South Region - Sweet 16"
    assert stage_name(["ALDS", "NLDS"]) == "Division Series"
    assert stage_name(["East Final", "West Final"]) == "Conference Finals"
    assert stage_name(["AFC Championship", "NFC Championship"]) == "Conference Championships"
    assert stage_name(["Stanley Cup Final"]) == "Stanley Cup Final"
    assert stage_name(["East Region - Sweet 16", "West Region - Sweet 16"]) == "Sweet 16"
    assert stage_name(["East 1st Round"]) == "1st Round"


def test_standings_request_divisions():
    client = RecordingStandingsClient()
    TeamSportAdapter(CFG.league("mlb"), client=client).standings()  # type: ignore[arg-type]
    assert client.params == {"level": 3, "sort": "winpercent:desc"}  # config.yaml standings_params


class RecordingStandingsClient:
    params: dict = {}

    def get(self, url, params=None, ttl=0):
        self.params = dict(params or {})
        return {}


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


def test_live_football_situation():
    from sportsdash.adapters.team_sport import _situation, _strip_team

    spot = {"down": 3, "distance": 7, "yardsToEndzone": 18, "downDistanceText": "3rd & 7 at DAL 18",
            "shortDownDistanceText": "3rd & 7", "team": {"id": "21"}}
    data = {
        "header": {"competitions": [{"competitors": [{"id": "6", "possession": False}, {"id": "21", "possession": True}]}]},
        "drives": {"current": {"description": "8 plays, 57 yards, 4:01", "team": {"id": "21"},
                               "plays": [{"text": " J.Hurts pass short right to A.Brown for 5 yards.", "end": spot}]}},
    }
    sit = _situation(data)
    assert (sit.possession, sit.down_distance, sit.yards_to_endzone, sit.red_zone) == ("21", "3rd & 7 at DAL 18", 18, True)
    assert sit.last_play == "J.Hurts pass short right to A.Brown for 5 yards."

    # Kickoff after a score: no down, possession falls back to the play's team.
    data["header"] = {}
    data["drives"]["current"]["plays"][0]["end"] = {"down": 0, "team": {"id": "6"}}
    sit = _situation(data)
    assert (sit.possession, sit.down_distance, sit.yards_to_endzone) == ("6", "", None)
    assert _situation({}) is None
    assert _strip_team("Minnesota Passing", {"displayName": "Minnesota Vikings", "location": "Minnesota"}) == "Passing"
    assert _strip_team("Passing", {"location": "Minnesota"}) == "Passing"
    assert sit.drive == ""  # the drive was PHI's, but DAL has the ball
