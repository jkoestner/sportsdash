"""Turn postseason scoreboard events into a bracket: stages (columns) of series.

ESPN has no bracket feed for most leagues, but every postseason game says enough:
  * notes[0].headline names the round:  "ALDS - Game 2", "East 1st Round - Game 4",
    "AFC Wild Card Playoffs", "College Football Playoff Quarterfinal at the Rose Bowl"
  * competitions[0].type.abbreviation is the stage in series sports: RD16, QTR, SEMI, FINAL
    (football and college basketball use STD/TRNMNT throughout, so their stage comes from
    the round name with the conference or region removed)
  * competitions[0].series has the best-of length, each team's wins and a summary
"""

from __future__ import annotations

import re

from ..models import Game, PlayoffSeries, PlayoffStage, SeriesTeam
from .parse import g, parse_event

_GAME_NO = re.compile(r"\s*-\s*Game\s+\d+.*$", re.I)  # "ALDS - Game 2"
_GAME_NUM = re.compile(r"\bGame\s+(\d+)", re.I)  # "ALCS - Game 7 If Necessary" -> 7
_EXTRAS = re.compile(r"\s+(at the|presented by)\s.*$", re.I)  # "... at the Rose Bowl Presented by ..."
_SUFFIX = re.compile(r"\s+(Game|Playoffs?)$", re.I)  # "First Round Game", "AFC Wild Card Playoffs"
# Conference or region prefix: "AFC Wild Card", "East 1st Round", "South Region - Sweet 16"
_CONF = re.compile(r"^([A-Za-z]+ Region\s*-\s*|(AFC|NFC|Eastern|Western|East|West|American League|National League)\s+)")
_MLB = re.compile(r"^(AL|NL)(WC|DS|CS)$")  # ALWC, NLDS, ALCS...
_MLB_NAMES = {"WC": "Wild Card", "DS": "Division Series", "CS": "Championship Series"}
_NOT_STAGES = {"", "STD", "TRNMNT"}  # type abbreviations that don't identify a stage
SKIP_NOTES = ("Pro Bowl", "All-Star")  # exhibitions ESPN files under the postseason


def round_name(note: str, match: str = "") -> str:
    """The round a game belongs to, without game numbers or sponsor text."""
    name = _EXTRAS.sub("", _GAME_NO.sub("", note or "").strip())
    if match and name.startswith(match):
        name = name[len(match):].strip(" -")  # "College Football Playoff Quarterfinal" -> "Quarterfinal"
    return _SUFFIX.sub("", name).strip() or "Playoffs"


def stage_name(rounds: list[str]) -> str:
    """Column title for rounds played at the same stage: ["ALDS", "NLDS"] -> "Division Series"."""
    names: list[str] = []
    conference = False
    for r in rounds:
        m = _MLB.match(r)
        name = _MLB_NAMES[m.group(2)] if m else _CONF.sub("", r)
        conference = conference or name != r
        if name not in names:
            names.append(name)
    if len(names) == 1 and conference:
        # "East Final" + "West Final" -> "Conference Finals", not just "Final"
        return {"Final": "Conference Finals", "Championship": "Conference Championships"}.get(names[0], names[0])
    return " / ".join(names)


def _stage_key(comp: dict, rnd: str) -> str:
    abbr = (g(comp, "type", "abbreviation", default="") or "").upper()
    return abbr if abbr not in _NOT_STAGES else stage_name([rnd])


def is_tbd(team_id: str) -> bool:
    """ESPN fills undecided matchups with placeholder teams whose ids are -1 and -2."""
    return not team_id or team_id.startswith("-")


def _series_team(t, wins: dict[str, int]) -> SeriesTeam:
    if is_tbd(t.id):
        return SeriesTeam(id="", name="TBD", short="TBD", abbr="TBD", logo="")
    return SeriesTeam(
        id=t.id, name=t.name, short=t.short, abbr=t.abbr, logo=t.logo, rank=t.rank, wins=wins.get(t.id, 0)
    )


def _series(rnd: str, games: list[tuple[Game, dict]]) -> PlayoffSeries:
    games = sorted(games, key=lambda p: (p[0].start is None, p[0].start))
    last_comp = games[-1][1]
    info = last_comp.get("series") or {}  # the latest game carries the current series state
    wins = {str(c.get("id")): int(c.get("wins") or 0) for c in info.get("competitors") or []}
    # TBD placeholder games carry no series data, but "ALCS - Game 7 If Necessary" gives the
    # length. Series are odd, so a listed game 6 still means best of 7.
    numbered = [int(m.group(1)) for gm, _ in games if (m := _GAME_NUM.search(gm.note))]
    best_of = int(info.get("totalCompetitions") or max(numbered, default=1) | 1)
    if not info:  # single game: the winner has one "win"
        for gm, _ in games:
            for t in (gm.home, gm.away):
                if gm.state == "post" and t.winner:
                    wins[t.id] = wins.get(t.id, 0) + 1
    finals = [gm for gm, _ in games if gm.state == "post"]
    completed = bool(info.get("completed")) if info else bool(finals) and len(finals) == len(games)
    if completed:  # "If Necessary" games that weren't
        games = [(gm, c) for gm, c in games if gm.state != "pre"]
    # The earliest game that names the most teams; its home team is the higher seed, so it
    # goes first like on a printed bracket.
    first = max((gm for gm, _ in games), key=lambda gm: sum(not is_tbd(t.id) for t in (gm.home, gm.away)))
    teams = [_series_team(t, wins) for t in (first.home, first.away)]
    if completed and teams[0].wins != teams[1].wins:
        max(teams, key=lambda t: t.wins).winner = True
    return PlayoffSeries(
        round=rnd,
        best_of=best_of,
        teams=teams,
        summary=info.get("summary") or "",
        completed=completed,
        games=[gm for gm, _ in games],
    )


def build_bracket(events: list[dict], league_key: str, match: str = "") -> tuple[list[PlayoffStage], list[Game]]:
    """Bracket stages in the order they were played, plus postseason games outside the bracket."""
    rows: list[tuple[Game, dict, str]] = []
    other: list[Game] = []
    for ev in events:
        gm = parse_event(ev, league_key)
        if gm is None or any(s in gm.note for s in SKIP_NOTES) or gm.detail.lower().startswith("cancel"):
            continue
        if match and match not in gm.note:
            other.append(gm)
            continue
        rows.append((gm, g(ev, "competitions", 0, default={}), round_name(gm.note, match)))

    by_series: dict[tuple, list[tuple[Game, dict]]] = {}
    stage_of: dict[tuple, str] = {}
    # Games between two known teams first, so a later "SEA vs TBD" game can join SEA's series.
    rows.sort(key=lambda r: any(is_tbd(t.id) for t in (r[0].home, r[0].away)))
    for gm, comp, rnd in rows:
        ids = frozenset((gm.home.id, gm.away.id))
        known = {i for i in ids if not is_tbd(i)}
        key = (rnd, ids)
        if len(known) < 2:
            key = next((k for k in by_series if k[0] == rnd and known & k[1]), key)
        by_series.setdefault(key, []).append((gm, comp))
        stage_of[key] = _stage_key(comp, rnd)

    stages: dict[str, list[PlayoffSeries]] = {}
    for key, games in by_series.items():
        stages.setdefault(stage_of[key], []).append(_series(key[0], games))

    out = []
    for series in stages.values():
        series.sort(key=lambda s: (s.round, _first_start(s)))  # AL before NL, East before West
        out.append(PlayoffStage(name=stage_name([s.round for s in series]), series=series))
    out.sort(key=lambda st: min(_first_start(s) for s in st.series))
    other.sort(key=lambda gm: (gm.start is None, gm.start))
    return out, other


def _first_start(series: PlayoffSeries) -> str:
    return min((gm.start.isoformat() for gm in series.games if gm.start), default="9999")


def _same_stage(name: str, template: str) -> bool:
    a, b = name.lower(), template.lower()
    return a.startswith(b) or b.startswith(a)  # "Super Bowl LX" is the "Super Bowl" stage


def pad_bracket(stages: list[PlayoffStage], template: dict[str, int]) -> list[PlayoffStage]:
    """Fill the bracket out to the final using the league's format (config `playoffs_rounds`):
    rounds ESPN hasn't scheduled yet, and matchups missing from a round, become TBD cards."""
    out = list(stages)
    prev = -1
    for name, count in template.items():
        idx = next((i for i, st in enumerate(out) if _same_stage(st.name, name)), None)
        if idx is None:
            idx = prev + 1
            out.insert(idx, PlayoffStage(name=name))
        stage = out[idx]
        for _ in range(int(count) - len(stage.series)):
            tbd = [SeriesTeam(id="", name="TBD", short="TBD", abbr="TBD", logo="") for _ in range(2)]
            stage.series.append(PlayoffSeries(round=stage.name, best_of=0, teams=tbd))
        prev = idx
    return out
