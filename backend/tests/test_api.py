"""API contract tests: the shapes frontend/src/types.ts relies on."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import conftest  # noqa: F401  (sets fixture env vars first)
from sportsdash.api import app

client = TestClient(app)


def test_config():
    r = client.get("/api/config").json()
    assert r["today"] == "2026-10-02"
    assert [lg["key"] for lg in r["leagues"]] == ["nfl", "ncaaf", "ncaab", "epl", "nhl", "mlb", "pga"]
    assert [lg["key"] for lg in r["leagues"] if lg["rankings"]] == ["ncaaf"]
    assert {t["short"] for t in r["teams"]} == {"UVA", "DAL"}
    assert r["teams"][0]["espn_id"] == "258"


def test_scores_shape():
    r = client.get("/api/scores", params={"date": "2026-10-03"}).json()
    assert r["date"] == "2026-10-03"
    uva = next(g for g in r["games"] if g["home"]["abbr"] == "UVA")
    assert uva["league"] == "ncaaf" and uva["state"] == "pre"
    assert uva["start"].startswith("2026-10-03T19:30:00")  # ISO, UTC
    assert uva["venue"] == "Scott Stadium" and uva["city"] == "Charlottesville, VA"
    assert uva["odds"]["details"] == "UVA -3" and uva["odds"]["over_under"] == 52.5
    assert r["tournaments"][0]["name"] == "Sanderson Farms Championship"


def test_scores_filters_to_local_day():
    # The 8:20 PM ET Sunday game is 00:20 UTC Monday; it must land on Sunday.
    sun = client.get("/api/scores", params={"date": "2026-10-04"}).json()
    assert any(g["id"] == "401772047" for g in sun["games"])
    mon = client.get("/api/scores", params={"date": "2026-10-05"}).json()
    assert not any(g["id"] == "401772047" for g in mon["games"])


def test_schedule_window():
    r = client.get("/api/schedule", params={"days": 3}).json()
    assert (r["start"], r["end"]) == ("2026-10-02", "2026-10-04")
    assert len(r["games"]) == len({g["id"] for g in r["games"]})


def test_standings():
    r = client.get("/api/standings/ncaaf").json()
    assert r["groups"][0]["name"] == "Atlantic Coast Conference"  # group with UVA first
    assert r["groups"][0]["parent"] == ""  # a conference with no divisions, not "FBS"
    nfl = client.get("/api/standings/nfl").json()["groups"]
    # Divisions, labeled with their conference; the Cowboys' conference first, their division on top.
    assert [(g["parent"], g["name"]) for g in nfl] == [
        ("National Football Conference", "NFC East"),
        ("National Football Conference", "NFC North"),
        ("American Football Conference", "AFC East"),
        ("American Football Conference", "AFC West"),
    ]
    golf = client.get("/api/standings/pga").json()
    assert golf["tournaments"][0]["players"][0]["name"] == "Ben Griffin"


def test_teams():
    panels = client.get("/api/teams").json()
    dal = next(p for p in panels if p["team"]["short"] == "DAL")
    assert dal["record"] == "3-1" and dal["next_game"]["id"] == "401772045"
    assert len(dal["next_odds"]) == 2


def test_rankings():
    r = client.get("/api/rankings/ncaaf").json()
    assert (r["name"], r["week"]) == ("AP Top 25", "Week 5")
    first = r["entries"][0]
    assert (first["rank"], first["abbr"], first["previous"], first["first_place_votes"]) == (2, "UGA", 3, 9)
    assert r["entries"][-1]["previous"] is None  # 0 = unranked last week
    assert client.get("/api/rankings/nfl").json() is None  # no poll configured


def test_scores_use_ap_ranks():
    games = client.get("/api/scores", params={"date": "2026-10-02"}).json()["games"]
    mia = next(g for g in games if g["away"]["abbr"] == "MIA")
    assert mia["away"]["rank"] == 10  # AP poll, not the scoreboard's curatedRank (12)
    assert mia["home"]["rank"] is None


def test_team_page_any_team():
    uga = client.get("/api/team/ncaaf/61").json()
    assert uga["team"]["name"] == "Georgia Bulldogs" and uga["team"]["color"] == "#ba0c2f"
    assert (uga["rank"], uga["standing"], uga["record"]) == (2, "1st in SEC", "1-0")
    assert uga["next_game"]["id"] == "401755150"
    assert uga["logo"].endswith("/61.png")
    uva = client.get("/api/team/ncaaf/258").json()
    assert uva["team"]["color"] == "#E57200"  # configured teams keep config.yaml's color


def test_playoffs_in_progress():
    r = client.get("/api/playoffs/mlb").json()
    assert r["season"] == 2026 and r["next_start"] is None
    # Out to the World Series, even though most of it hasn't been decided.
    assert [s["name"] for s in r["stages"]] == ["Wild Card", "Division Series", "Championship Series", "World Series"]
    assert [len(s["series"]) for s in r["stages"]] == [4, 4, 2, 1]  # config.yaml playoffs_rounds
    wc = r["stages"][0]["series"]
    assert [s["round"] for s in wc[:2]] == ["ALWC", "NLWC"]  # AL side first
    det = wc[0]
    assert [(t["abbr"], t["wins"], t["winner"]) for t in det["teams"]] == [("CLE", 0, False), ("DET", 2, True)]
    assert det["completed"] and det["best_of"] == 3
    assert [g["id"] for g in det["games"]] == ["401800001", "401800002"]  # unplayed "if necessary" game 3 dropped
    chc = wc[1]
    assert not chc["completed"] and chc["summary"] == "Series tied 1-1"
    assert chc["games"][-1]["state"] == "in"
    ds = r["stages"][1]["series"]
    alds, nlds = ds[0], ds[1]
    assert alds["best_of"] == 5 and [t["abbr"] for t in alds["teams"]] == ["SEA", "DET"]
    # Undecided opponent: one series with both games, and a TBD team that links nowhere.
    assert [(t["abbr"], t["id"]) for t in nlds["teams"]] == [("LAD", "19"), ("TBD", "")]
    assert len(nlds["games"]) == 2
    # Rounds ESPN hasn't filled in are placeholder cards with no games.
    assert [(s["best_of"], s["games"]) for s in ds[2:]] == [(0, []), (0, [])]
    alcs = r["stages"][2]["series"][0]
    assert alcs["round"] == "ALCS" and len(alcs["games"]) == 2 and alcs["teams"][0]["name"] == "TBD"
    assert alcs["best_of"] == 7  # no series data on TBD games: read from "ALCS - Game N" notes
    ws = r["stages"][3]["series"][0]
    assert ws["best_of"] == 7 and [g["note"] for g in ws["games"]][-1].endswith("If Necessary")
    assert all("All-Star" not in g["note"] for st in r["stages"] for s in st["series"] for g in s["games"])


def test_playoffs_before_they_start():
    # NHL preseason: show last season's playoffs and when the next ones begin.
    r = client.get("/api/playoffs/nhl").json()
    assert r["season"] == 2026 and r["next_start"].startswith("2027-04-11")
    assert r["stages"] == []  # no 2026 playoff games in the fixtures
    assert client.get("/api/playoffs/epl").json() is None  # playoffs: false
    assert client.get("/api/playoffs/nfl").json() is None  # ESPN has no postseason dates here
    cfg = {lg["key"]: lg["playoffs"] for lg in client.get("/api/config").json()["leagues"]}
    assert (cfg["mlb"], cfg["epl"], cfg["pga"]) == (True, False, False)


def test_game_detail():
    r = client.get("/api/game/nfl/401772001").json()
    assert r["game"]["away"]["score"] == "27"
    assert r["team_stats"][0] == ["1st Downs", "22", "18"]
    assert r["plays"][0]["period"] == "Q1" and len(r["win_prob"]) == 18


@pytest.mark.parametrize(
    "path,code",
    [("/api/game/nfl/999", 404), ("/api/game/xfl/1", 404), ("/api/scores?date=nope", 400),
     ("/api/golf/pga/401703510", 200), ("/api/golf/nfl/1", 404),
     ("/api/team/ncaaf/999", 404), ("/api/team/pga/1", 404), ("/api/team/xfl/1", 404), ("/api/nope", 404), ("/api/schedule?days=99", 422)],
)
def test_status_codes(path, code):
    assert client.get(path).status_code == code


def test_spa_fallback_and_assets(tmp_path, monkeypatch):
    import sportsdash.api as api

    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<div id=root></div>")
    (tmp_path / "assets" / "app-123.js").write_text("console.log(1)")
    monkeypatch.setattr(api, "STATIC", tmp_path)

    deep = client.get("/game/nfl/401772001")  # client-side route -> index.html
    assert deep.status_code == 200 and "root" in deep.text
    js = client.get("/assets/app-123.js")
    assert js.status_code == 200 and "immutable" in js.headers["cache-control"]
    assert client.get("/assets/old-999.js").status_code == 404
    assert client.get("/../config.yaml").status_code in (200, 404)  # never serves files outside dist
    assert "timezone" not in client.get("/%2e%2e/config.yaml").text
