"""JSON API for the React frontend, plus static hosting of the built SPA.

Run for development:   uvicorn sportsdash.api:app --reload --port 8000
All responses use the dataclass field names from models.py (snake_case);
frontend/src/types.ts mirrors them.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse

from . import __version__, data
from .adapters import adapter_for
from .config import AppConfig, LeagueConfig, load_config

log = logging.getLogger(__name__)
if not logging.getLogger("sportsdash").handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))  # matches uvicorn's style
    logging.getLogger("sportsdash").addHandler(_h)
    logging.getLogger("sportsdash").setLevel(logging.INFO)

cfg: AppConfig = load_config()
app = FastAPI(title="sportsdash", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json")


# ── helpers ──────────────────────────────────────────────────────────────────


def today() -> date:
    override = os.environ.get("SPORTSDASH_TODAY")  # fixture mode: pin "today"
    return date.fromisoformat(override) if override else datetime.now(cfg.tz).date()


def out(obj: Any) -> Any:
    """Dataclasses -> dicts -> JSON-safe (datetimes become ISO 8601 strings in UTC)."""
    if is_dataclass(obj) and not isinstance(obj, type):
        obj = asdict(obj)
    elif isinstance(obj, list):
        obj = [asdict(o) if is_dataclass(o) and not isinstance(o, type) else o for o in obj]
    return jsonable_encoder(obj)


def league_or_404(key: str) -> LeagueConfig:
    try:
        return cfg.league(key)
    except KeyError:
        raise HTTPException(404, f"League '{key}' isn't in config.yaml") from None


def parse_day(value: str | None) -> date:
    if not value:
        return today()
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD") from None


# ── routes ───────────────────────────────────────────────────────────────────


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "version": __version__}


@app.get("/api/config")
def get_config() -> dict:
    return {
        "today": today().isoformat(),
        "timezone": cfg.timezone,
        "refresh_seconds": cfg.refresh_seconds,
        "schedule_days": cfg.schedule_days,
        "leagues": [
            {
                "key": lg.key,
                "name": lg.name,
                "sport": lg.sport,
                "kind": lg.kind,
                "rankings": lg.rankings,
                "playoffs": lg.playoffs and not lg.is_golf,
            }
            for lg in cfg.leagues
        ],
        "teams": out(cfg.teams),
    }


@app.get("/api/scores")
def get_scores(day: str | None = Query(None, alias="date")) -> dict:
    d = parse_day(day)
    games = data.games_between(cfg, d, d)
    tours = data.tournaments_between(cfg, d, d)
    return {
        "date": d.isoformat(),
        "games": out([gm for lst in games.values() for gm in lst]),
        "tournaments": out([t for lst in tours.values() for t in lst]),
    }


@app.get("/api/schedule")
def get_schedule(days: int = Query(None, ge=1, le=31)) -> dict:
    start = today()
    end = start + timedelta(days=(days or cfg.schedule_days) - 1)
    games = data.games_between(cfg, start, end)
    tours = data.tournaments_between(cfg, start, end)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "games": out([gm for lst in games.values() for gm in lst]),
        "tournaments": out([t for lst in tours.values() for t in lst]),
    }


@app.get("/api/standings/{league}")
def get_standings(league: str) -> dict:
    lg = league_or_404(league)
    if lg.is_golf:
        return {"league": lg.key, "groups": [], "tournaments": out(adapter_for(lg).current())}
    return {"league": lg.key, "groups": out(data.standings(cfg, lg.key)), "tournaments": []}


@app.get("/api/teams")
def get_teams() -> list:
    return out(data.team_panels(cfg))


@app.get("/api/team/{league}/{team_id}")
def get_team(league: str, team_id: str) -> dict:
    lg = league_or_404(league)
    if lg.is_golf:
        raise HTTPException(404, "Golf has no teams")
    panel = data.team_panel(cfg, lg, team_id)
    if panel is None:
        raise HTTPException(404, "ESPN doesn't have a schedule for this team.")
    return out(panel)


@app.get("/api/rankings/{league}")
def get_rankings(league: str) -> dict | None:
    lg = league_or_404(league)
    if lg.is_golf:
        return None
    return out(adapter_for(lg).poll())  # null when the league has no poll configured


@app.get("/api/playoffs/{league}")
def get_playoffs(league: str) -> dict | None:
    lg = league_or_404(league)
    if lg.is_golf or not lg.playoffs:
        return None
    return out(adapter_for(lg).playoffs(today()))  # null when ESPN has no postseason


@app.get("/api/game/{league}/{event_id}")
def get_game(league: str, event_id: str) -> dict:
    lg = league_or_404(league)
    if lg.is_golf:
        raise HTTPException(404, "Use /api/golf for tournaments")
    detail = adapter_for(lg).detail(event_id)
    if detail is None:
        raise HTTPException(404, "ESPN didn't return this game. It may not be published yet.")
    return out(detail)


@app.get("/api/golf/{league}/{event_id}")
def get_golf(league: str, event_id: str) -> dict:
    lg = league_or_404(league)
    if not lg.is_golf:
        raise HTTPException(404, "Not a golf league")
    t = adapter_for(lg).leaderboard(event_id)
    if t is None:
        raise HTTPException(404, "ESPN didn't return this tournament.")
    return out(t)


@app.exception_handler(Exception)
def unhandled(_request, exc: Exception) -> JSONResponse:
    log.exception("API error: %s", exc)
    return JSONResponse({"detail": "Server error. Check the container logs."}, status_code=500)


# ── built frontend (production) ──────────────────────────────────────────────
# In development Vite serves the frontend and proxies /api here, so this is unused.

STATIC = Path(os.environ.get("SPORTSDASH_STATIC", Path(__file__).resolve().parents[2] / "frontend" / "dist"))


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "Unknown API route")
    if not STATIC.exists():
        return JSONResponse(
            {"detail": "Frontend not built. Run `npm run build` in frontend/, or use `npm run dev` on port 5173."},
            status_code=404,
        )
    target = (STATIC / path).resolve()
    if path and target.is_file() and STATIC.resolve() in target.parents:
        # Vite fingerprints asset filenames, so they can be cached forever.
        cache = "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
        return FileResponse(target, headers={"Cache-Control": cache})
    if path.startswith("assets/"):
        # A stale tab asking for an old build's bundle should get a clean 404, not index.html.
        raise HTTPException(404, "Asset not found")
    # Client-side routes (/teams, /game/nfl/123...) all load index.html; React Router takes over.
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})
