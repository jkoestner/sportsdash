"""League adapter registry: one adapter instance per configured league."""

from __future__ import annotations

from ..config import AppConfig, LeagueConfig
from .golf import GolfAdapter
from .team_sport import TeamSportAdapter

_cache: dict[str, TeamSportAdapter | GolfAdapter] = {}


def adapter_for(cfg: LeagueConfig) -> TeamSportAdapter | GolfAdapter:
    if cfg.key not in _cache:
        _cache[cfg.key] = GolfAdapter(cfg) if cfg.is_golf else TeamSportAdapter(cfg)
    return _cache[cfg.key]


def team_adapters(app_cfg: AppConfig) -> list[TeamSportAdapter]:
    return [adapter_for(lg) for lg in app_cfg.leagues if not lg.is_golf]  # type: ignore[misc]


def golf_adapters(app_cfg: AppConfig) -> list[GolfAdapter]:
    return [adapter_for(lg) for lg in app_cfg.leagues if lg.is_golf]  # type: ignore[misc]


__all__ = ["adapter_for", "team_adapters", "golf_adapters", "TeamSportAdapter", "GolfAdapter"]
