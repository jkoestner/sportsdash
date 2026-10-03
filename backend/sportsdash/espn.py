"""Small cached client for ESPN's public (unofficial, keyless) JSON endpoints.

Two bases are used:
  * site API  -> scoreboard, summary, team schedule
  * v2 API    -> standings (the site API's standings route returns a stub)

Set SPORTSDASH_FIXTURES=/path/to/dir to serve responses from JSON files instead
of the network (used by the tests and for offline development).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from urllib.parse import urlencode
from pathlib import Path

import requests

log = logging.getLogger(__name__)

SITE = "https://site.api.espn.com/apis/site/v2/sports"
V2 = "https://site.api.espn.com/apis/v2/sports"

# Cache lifetimes (seconds)
TTL_LIVE = 30
TTL_SCHEDULE = 600
TTL_STANDINGS = 3600


def fixture_key(url: str, params: dict | None) -> str:
    """Map a request to a fixture filename, e.g. football__nfl__summary__401.json."""
    tail = url.split("/sports/", 1)[-1].strip("/")
    key = tail.replace("/", "__")
    if params and "event" in params:
        key += f"__{params['event']}"
    return key + ".json"


class EspnClient:
    def __init__(self, fixtures_dir: str | None = None, timeout: float = 10.0):
        fixtures_dir = fixtures_dir or os.environ.get("SPORTSDASH_FIXTURES")
        self.fixtures = Path(fixtures_dir) if fixtures_dir else None
        self.timeout = timeout
        self._cache: dict[str, tuple[float, dict]] = {}
        self._lock = threading.Lock()
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "sportsdash/0.1 (+self-hosted)"

    def get(self, url: str, params: dict | None = None, ttl: int = TTL_LIVE) -> dict:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        cache_key = url + "?" + "&".join(f"{k}={params[k]}" for k in sorted(params))
        now = time.time()
        with self._lock:
            hit = self._cache.get(cache_key)
            if hit and now - hit[0] < ttl:
                return hit[1]

        try:
            data = self._fetch(url, params)
        except Exception as exc:  # network, HTTP or JSON errors
            log.warning("ESPN request failed %s %s: %s", url, params, exc)
            # Serve stale data rather than nothing if we have it.
            return hit[1] if hit else {}

        with self._lock:
            self._cache[cache_key] = (now, data)
        return data

    def _fetch(self, url: str, params: dict) -> dict:
        if self.fixtures is not None:
            path = self.fixtures / fixture_key(url, params)
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        t0 = time.perf_counter()
        resp = self._session.get(url, params=params, timeout=self.timeout)
        ms = (time.perf_counter() - t0) * 1000
        # One line per real ESPN call (cache hits are silent), e.g.
        #   ESPN 200  212ms football/nfl/scoreboard?dates=20261004&limit=500
        short = url.split("/sports/", 1)[-1] + (f"?{urlencode(params)}" if params else "")
        log.info("ESPN %s %5.0fms %s", resp.status_code, ms, short)
        resp.raise_for_status()
        return resp.json()


_client: EspnClient | None = None


def client() -> EspnClient:
    global _client
    if _client is None:
        _client = EspnClient()
    return _client
