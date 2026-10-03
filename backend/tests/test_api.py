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
    assert [lg["key"] for lg in r["leagues"]] == ["nfl", "ncaaf", "ncaab", "epl", "pga"]
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
    golf = client.get("/api/standings/pga").json()
    assert golf["tournaments"][0]["players"][0]["name"] == "Ben Griffin"


def test_teams():
    panels = client.get("/api/teams").json()
    dal = next(p for p in panels if p["team"]["short"] == "DAL")
    assert dal["record"] == "3-1" and dal["next_game"]["id"] == "401772045"
    assert len(dal["next_odds"]) == 2


def test_game_detail():
    r = client.get("/api/game/nfl/401772001").json()
    assert r["game"]["away"]["score"] == "27"
    assert r["team_stats"][0] == ["1st Downs", "22", "18"]
    assert r["plays"][0]["period"] == "Q1" and len(r["win_prob"]) == 18


@pytest.mark.parametrize(
    "path,code",
    [("/api/game/nfl/999", 404), ("/api/game/xfl/1", 404), ("/api/scores?date=nope", 400),
     ("/api/golf/pga/401703510", 200), ("/api/golf/nfl/1", 404), ("/api/nope", 404), ("/api/schedule?days=99", 422)],
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
