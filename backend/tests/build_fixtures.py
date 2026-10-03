"""Generate ESPN-shaped fixture JSON for offline development and tests.

Shapes mirror ESPN's public site/v2 and v2 endpoints. Matchups, scores and odds are
SAMPLE data, not real results.

    python tests/build_fixtures.py   # writes tests/fixtures/*.json
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).parent / "fixtures"
CDN = "https://a.espncdn.com/i/teamlogos"


def team(tid, name, short, abbr, logo_path):
    return {
        "id": str(tid),
        "displayName": name,
        "shortDisplayName": short,
        "abbreviation": abbr,
        "logo": f"{CDN}/{logo_path}",
    }


TEAMS = {
    # NFL
    "DAL": team(6, "Dallas Cowboys", "Cowboys", "DAL", "nfl/500/dal.png"),
    "GB": team(9, "Green Bay Packers", "Packers", "GB", "nfl/500/gb.png"),
    "PHI": team(21, "Philadelphia Eagles", "Eagles", "PHI", "nfl/500/phi.png"),
    "KC": team(12, "Kansas City Chiefs", "Chiefs", "KC", "nfl/500/kc.png"),
    "BUF": team(2, "Buffalo Bills", "Bills", "BUF", "nfl/500/buf.png"),
    "NYG": team(19, "New York Giants", "Giants", "NYG", "nfl/500/nyg.png"),
    "WSH": team(28, "Washington Commanders", "Commanders", "WSH", "nfl/500/wsh.png"),
    # College
    "UVA": team(258, "Virginia Cavaliers", "Virginia", "UVA", "ncaa/500/258.png"),
    "VT": team(259, "Virginia Tech Hokies", "Virginia Tech", "VT", "ncaa/500/259.png"),
    "UNC": team(153, "North Carolina Tar Heels", "North Carolina", "UNC", "ncaa/500/153.png"),
    "CLEM": team(228, "Clemson Tigers", "Clemson", "CLEM", "ncaa/500/228.png"),
    "MIA": team(2390, "Miami Hurricanes", "Miami", "MIA", "ncaa/500/2390.png"),
    "LOU": team(97, "Louisville Cardinals", "Louisville", "LOU", "ncaa/500/97.png"),
    "UGA": team(61, "Georgia Bulldogs", "Georgia", "UGA", "ncaa/500/61.png"),
    "BAMA": team(333, "Alabama Crimson Tide", "Alabama", "ALA", "ncaa/500/333.png"),
    "DUKE": team(150, "Duke Blue Devils", "Duke", "DUKE", "ncaa/500/150.png"),
    "COAST": team(324, "Coastal Carolina Chanticleers", "Coastal Carolina", "CCU", "ncaa/500/324.png"),
    # EPL
    "ARS": team(359, "Arsenal", "Arsenal", "ARS", "soccer/500/359.png"),
    "LIV": team(364, "Liverpool", "Liverpool", "LIV", "soccer/500/364.png"),
    "MCI": team(382, "Manchester City", "Man City", "MCI", "soccer/500/382.png"),
    "CHE": team(363, "Chelsea", "Chelsea", "CHE", "soccer/500/363.png"),
    "TOT": team(367, "Tottenham Hotspur", "Spurs", "TOT", "soccer/500/367.png"),
    "NEW": team(361, "Newcastle United", "Newcastle", "NEW", "soccer/500/361.png"),
}


def status(state, short, name="STATUS_SCHEDULED", period=0, clock="0:00"):
    return {
        "clock": 0,
        "displayClock": clock,
        "period": period,
        "type": {"state": state, "name": name, "shortDetail": short, "detail": short, "completed": state == "post"},
    }


def competitor(abbr, home_away, score=None, record="", rank=None, winner=None, lines=None, schedule_shape=False):
    c = {"homeAway": home_away, "team": TEAMS[abbr]}
    if score is not None:
        c["score"] = {"value": float(score), "displayValue": str(score)} if schedule_shape else str(score)
    if record:
        if schedule_shape:
            c["record"] = [{"type": "total", "displayValue": record}]
        else:
            c["records"] = [{"type": "total", "summary": record}]
    if rank:
        c["curatedRank"] = {"current": rank}
    if winner is not None:
        c["winner"] = winner
    if lines:
        c["linescores"] = [{"value": float(v), "displayValue": str(v)} for v in lines]
    return c


def odds(details, ou, spread, home_ml, away_ml, draw_ml=None, provider="ESPN BET"):
    o = {
        "provider": {"id": "58", "name": provider},
        "details": details,
        "overUnder": ou,
        "spread": spread,
        "homeTeamOdds": {"moneyLine": home_ml},
        "awayTeamOdds": {"moneyLine": away_ml},
    }
    if draw_ml is not None:
        o["drawOdds"] = {"moneyLine": draw_ml}
    return o


def venue(name, city, state=None, country=None):
    addr = {"city": city}
    if state:
        addr["state"] = state
    if country:
        addr["country"] = country
    return {"id": "1", "fullName": name, "address": addr}


def event(eid, date, home, away, st, v, odds_=None, tv=None, note=None, neutral=False, **kw):
    comp = {
        "id": eid,
        "date": date,
        "timeValid": True,
        "neutralSite": neutral,
        "venue": v,
        "competitors": [competitor(home, "home", **kw.get("h", {})), competitor(away, "away", **kw.get("a", {}))],
        "status": st,
        "broadcasts": [{"market": "national", "names": tv}] if tv else [],
    }
    if odds_:
        comp["odds"] = [odds_]
    if note:
        comp["notes"] = [{"type": "event", "headline": note}]
    return {
        "id": eid,
        "date": date,
        "name": f"{TEAMS[away]['displayName']} at {TEAMS[home]['displayName']}",
        "shortName": f"{away} @ {home}",
        "competitions": [comp],
        "status": st,
    }


def write(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=1))


# ── NFL ──────────────────────────────────────────────────────────────────────
NFL_FINAL = event(
    "401772001", "2026-09-27T20:25Z", "PHI", "DAL", status("post", "Final", "STATUS_FINAL", 4),
    venue("Lincoln Financial Field", "Philadelphia", "PA"), odds("PHI -3.5", 47.5, -3.5, -180, 150), ["FOX"],
    h={"score": 20, "record": "3-1", "winner": False, "lines": [7, 3, 7, 3]},
    a={"score": 27, "record": "3-1", "winner": True, "lines": [3, 14, 0, 10]},
)
NFL_DAL_NEXT = event(
    "401772045", "2026-10-04T20:25Z", "DAL", "GB", status("pre", "Sun, October 4th at 4:25 PM EDT"),
    venue("AT&T Stadium", "Arlington", "TX"), odds("DAL -2.5", 49.5, -2.5, -142, 120), ["CBS"],
    h={"record": "3-1"}, a={"record": "2-2"},
)
NFL_OTHER = event(
    "401772046", "2026-10-04T17:00Z", "BUF", "KC", status("pre", "Sun, October 4th at 1:00 PM EDT"),
    venue("Highmark Stadium", "Orchard Park", "NY"), odds("BUF -1.5", 51.5, -1.5, -125, 105), ["CBS"],
    h={"record": "4-0"}, a={"record": "3-1"},
)
NFL_SNF = event(
    "401772047", "2026-10-05T00:20Z", "WSH", "NYG", status("pre", "Sun, October 4th at 8:20 PM EDT"),
    venue("Northwest Stadium", "Landover", "MD"), odds("WSH -6.5", 44.5, -6.5, -290, 235), ["NBC", "Peacock"],
    h={"record": "2-2"}, a={"record": "1-3"},
)
nfl_calendar = [{"label": "Regular Season", "entries": [{"label": "Week 5", "startDate": "2026-09-30T07:00Z"}]}]
write("football__nfl__scoreboard.json", {
    "leagues": [{"id": "28", "abbreviation": "NFL", "calendar": nfl_calendar}],
    "week": {"number": 5},
    "events": [NFL_FINAL, NFL_OTHER, NFL_DAL_NEXT, NFL_SNF],
})

# ── NCAAF ────────────────────────────────────────────────────────────────────
CFB_FRI = event(
    "401755101", "2026-10-02T23:30Z", "LOU", "MIA", status("in", "8:42 - 2nd", "STATUS_IN_PROGRESS", 2, "8:42"),
    venue("L&N Federal Credit Union Stadium", "Louisville", "KY"), odds("MIA -4.5", 55.5, 4.5, 160, -190), ["ESPN"],
    h={"score": 10, "record": "3-1", "lines": [7, 3]}, a={"score": 14, "record": "4-0", "rank": 12, "lines": [7, 7]},
)
CFB_UVA = event(
    "401755140", "2026-10-03T19:30Z", "UVA", "UNC", status("pre", "Sat, October 3rd at 3:30 PM EDT"),
    venue("Scott Stadium", "Charlottesville", "VA"), odds("UVA -3", 52.5, -3.0, -155, 130), ["ACCN"],
    h={"record": "3-1"}, a={"record": "2-2"}, note="South's Oldest Rivalry",
)
CFB_BIG = event(
    "401755150", "2026-10-03T23:30Z", "BAMA", "UGA", status("pre", "Sat, October 3rd at 7:30 PM EDT"),
    venue("Bryant-Denny Stadium", "Tuscaloosa", "AL"), odds("UGA -1.5", 48.5, 1.5, 102, -122), ["ABC"],
    h={"record": "4-0", "rank": 4}, a={"record": "4-0", "rank": 2},
)
write("football__college-football__scoreboard.json", {
    "leagues": [{"id": "23", "abbreviation": "NCAAF"}],
    "events": [CFB_FRI, CFB_UVA, CFB_BIG],
})

# ── NCAAB (preseason: empty scoreboard) ──────────────────────────────────────
# AP poll (rankings endpoint). Released Sept 27, so it re-ranks every game after that.
# MIA is 12th on the scoreboard (curatedRank) but 10th here: the AP rank should win.
def poll_rank(abbr, current, previous, record, points, fpv=0):
    t = TEAMS[abbr]
    return {
        "current": current, "previous": previous, "points": points, "firstPlaceVotes": fpv,
        "recordSummary": record,
        "team": {"id": t["id"], "location": t["shortDisplayName"], "nickname": t["shortDisplayName"],
                 "abbreviation": t["abbreviation"], "logo": t["logo"]},
    }


write("football__college-football__rankings.json", {"rankings": [
    {"id": "1", "name": "AP Top 25", "shortName": "AP Poll", "type": "ap", "date": "2026-09-27T07:00Z",
     "occurrence": {"number": 5, "type": "week", "displayValue": "Week 5"},
     "ranks": [
         poll_rank("UGA", 2, 3, "4-0", 1580, 9),
         poll_rank("BAMA", 4, 4, "4-0", 1490),
         poll_rank("MIA", 10, 12, "4-0", 1010),
         poll_rank("CLEM", 18, 0, "3-1", 460),
     ]},
    {"id": "2", "name": "AFCA Coaches Poll", "shortName": "AFCA Coaches Poll", "type": "usa", "date": "2026-09-28T07:00Z",
     "occurrence": {"number": 5, "type": "week", "displayValue": "Week 5"},
     "ranks": [poll_rank("BAMA", 1, 1, "4-0", 1600, 40)]},
]})

write("basketball__mens-college-basketball__scoreboard.json", {"leagues": [{"abbreviation": "NCAAM"}], "events": []})

# ── EPL ──────────────────────────────────────────────────────────────────────
EPL_LIVE = event(
    "740901", "2026-10-02T19:00Z", "NEW", "CHE", status("in", "67'", "STATUS_SECOND_HALF", 2, "67'"),
    venue("St James' Park", "Newcastle-upon-Tyne", country="England"),
    odds("NEW +130", 2.5, None, 130, 210, draw_ml=240, provider="DraftKings"), ["Peacock"],
    h={"score": 1, "record": "4-1-1"}, a={"score": 1, "record": "3-2-1"},
)
EPL_SAT = event(
    "740905", "2026-10-03T11:30Z", "ARS", "LIV", status("pre", "Sat, October 3rd at 7:30 AM EDT"),
    venue("Emirates Stadium", "London", country="England"),
    odds("ARS -120", 2.5, None, -120, 310, draw_ml=280, provider="DraftKings"), ["NBC"],
    h={"record": "5-1-0"}, a={"record": "4-1-1"},
)
EPL_SUN = event(
    "740908", "2026-10-04T15:30Z", "TOT", "MCI", status("pre", "Sun, October 4th at 11:30 AM EDT"),
    venue("Tottenham Hotspur Stadium", "London", country="England"),
    odds("MCI -145", 3.5, None, 340, -145, draw_ml=300, provider="DraftKings"), ["USA Net"],
    h={"record": "2-2-2"}, a={"record": "4-0-2"},
)
write("soccer__eng.1__scoreboard.json", {"leagues": [{"abbreviation": "EPL"}], "events": [EPL_LIVE, EPL_SAT, EPL_SUN]})

# ── MLB postseason (in progress on 2026-10-02) ──────────────────────────────
# Postseason games carry season.type 3, the round in notes, and series state.
for abbr, tid, name, short in [
    ("NYY", 10, "New York Yankees", "Yankees"), ("BOS", 2, "Boston Red Sox", "Red Sox"),
    ("DET", 6, "Detroit Tigers", "Tigers"), ("CLE", 5, "Cleveland Guardians", "Guardians"),
    ("SEA", 12, "Seattle Mariners", "Mariners"), ("LAD", 19, "Los Angeles Dodgers", "Dodgers"),
    ("CIN", 17, "Cincinnati Reds", "Reds"), ("CHC", 16, "Chicago Cubs", "Cubs"), ("SD", 25, "San Diego Padres", "Padres"),
]:
    TEAMS[abbr] = team(tid, name, short, abbr, f"mlb/500/{abbr.lower()}.png")
# ESPN's placeholders for undecided matchups
TEAMS["TBD1"] = {"id": "-1", "displayName": "TBD", "shortDisplayName": "TBD", "abbreviation": "TBD"}
TEAMS["TBD2"] = {"id": "-2", "displayName": "TBD", "shortDisplayName": "TBD", "abbreviation": "TBD"}


def post_event(eid, date, home, away, st, note, stage, best_of, wins, summary="", hs=None, as_=None, done=False):
    """A postseason game. `wins` is each team's series wins after this game, (home, away)."""
    hw = None if hs is None or st["type"]["state"] != "post" else hs > as_
    ev = event(eid, date, home, away, st, venue("Ballpark", "City", "ST"), tv=["TBS"],
               h={"score": hs, "winner": hw}, a={"score": as_, "winner": None if hw is None else not hw})
    comp = ev["competitions"][0]
    comp["type"] = {"abbreviation": stage}
    comp["notes"] = [{"type": "event", "headline": note}]
    ev["season"] = {"year": 2026, "type": 3}
    if TEAMS[home]["id"].startswith("-"):  # ESPN sends no series data for TBD matchups
        return ev
    comp["series"] = {"type": "playoff", "summary": summary, "completed": done, "totalCompetitions": best_of,
                      "competitors": [{"id": TEAMS[home]["id"], "wins": wins[0]}, {"id": TEAMS[away]["id"], "wins": wins[1]}]}
    return ev


FINAL_MLB = lambda: status("post", "Final", "STATUS_FINAL")  # noqa: E731
MLB_POST = [
    # ALWC: DET sweeps CLE
    post_event("401800001", "2026-09-29T17:00Z", "CLE", "DET", FINAL_MLB(), "ALWC - Game 1", "RD16", 3, (0, 1), "DET leads series 1-0", 2, 5),
    post_event("401800002", "2026-09-30T17:00Z", "CLE", "DET", FINAL_MLB(), "ALWC - Game 2", "RD16", 3, (0, 2), "DET wins series 2-0", 1, 3, done=True),
    # ...so ESPN's still-listed game 3 never happens and must not show
    post_event("401800003", "2026-10-01T17:00Z", "CLE", "DET", status("pre", "Thu, Oct 1"),
               "ALWC - Game 3 If Necessary", "RD16", 3, (0, 2), "DET wins series 2-0", done=True),
    # NLWC: CHC v SD tied 1-1, game 3 live
    post_event("401800011", "2026-09-29T23:00Z", "CHC", "SD", FINAL_MLB(), "NLWC - Game 1", "RD16", 3, (1, 0), "CHC lead series 1-0", 4, 1),
    post_event("401800012", "2026-09-30T23:00Z", "CHC", "SD", FINAL_MLB(), "NLWC - Game 2", "RD16", 3, (1, 1), "Series tied 1-1", 0, 3),
    post_event("401800013", "2026-10-02T23:00Z", "CHC", "SD", status("in", "Top 7th", "STATUS_IN_PROGRESS", 7),
               "NLWC - Game 3", "RD16", 3, (1, 1), "Series tied 1-1", 2, 2),
    # ALDS game 1 is scheduled; the other side of the bracket is still to be decided
    post_event("401800021", "2026-10-04T20:00Z", "SEA", "DET", status("pre", "Sat, October 4th at 4:08 PM EDT"),
               "ALDS - Game 1", "QTR", 5, (0, 0)),
    # NLDS: LAD waits for the CHC/SD winner
    post_event("401800031", "2026-10-04T23:00Z", "LAD", "TBD1", status("pre", "Sat, Oct 4"), "NLDS - Game 1", "QTR", 5, (0, 0)),
    post_event("401800032", "2026-10-05T23:00Z", "LAD", "TBD1", status("pre", "Sun, Oct 5"), "NLDS - Game 2", "QTR", 5, (0, 0)),
    # Later rounds are on the schedule with no teams yet
    post_event("401800041", "2026-10-12T23:00Z", "TBD1", "TBD2", status("pre", "TBD"), "ALCS - Game 1", "SEMI", 7, (0, 0)),
    post_event("401800047", "2026-10-20T23:00Z", "TBD1", "TBD2", status("pre", "TBD"), "ALCS - Game 7 If Necessary", "SEMI", 7, (0, 0)),
    post_event("401800051", "2026-10-23T23:00Z", "TBD1", "TBD2", status("pre", "TBD"), "World Series - Game 1", "FINAL", 7, (0, 0)),
    post_event("401800056", "2026-10-30T23:00Z", "TBD1", "TBD2", status("pre", "TBD"),
               "World Series - Game 6 If Necessary", "FINAL", 7, (0, 0)),
    # An exhibition ESPN files under the postseason: never part of the bracket
    post_event("401800099", "2026-10-03T00:00Z", "LAD", "CIN", status("pre", "Sat, Oct 3"), "MLB All-Star Exhibition", "STD", 1, (0, 0)),
]
write("baseball__mlb__scoreboard.json", {
    "leagues": [{"abbreviation": "MLB", "season": {"year": 2026, "type": {"type": 3, "name": "Postseason"}}}],
    "events": MLB_POST,
})
# Core API season type: when the postseason runs.
write("baseball__leagues__mlb__seasons__2026__types__3.json",
      {"name": "Postseason", "startDate": "2026-09-29T07:00Z", "endDate": "2026-11-12T07:59Z"})

# ── NHL: preseason, so the Playoffs page shows last season's (empty here) ─────
write("hockey__nhl__scoreboard.json", {"leagues": [{"abbreviation": "NHL", "season": {"year": 2027, "type": {"type": 1}}}], "events": []})
write("hockey__leagues__nhl__seasons__2027__types__3.json",
      {"name": "Postseason", "startDate": "2027-04-11T07:00Z", "endDate": "2027-07-01T06:59Z"})
write("hockey__leagues__nhl__seasons__2026__types__3.json",
      {"name": "Postseason", "startDate": "2026-04-18T07:00Z", "endDate": "2026-07-01T06:59Z"})

# ── Golf ─────────────────────────────────────────────────────────────────────
def golfer(order, name, pos, score, rounds, thru="", today=""):
    lines = [{"value": float(r), "displayValue": str(r)} for r in rounds]
    if today:
        lines.append({"value": 0, "displayValue": today})
    return {
        "id": str(1000 + order), "order": order, "score": score,
        "athlete": {"displayName": name, "flag": {"href": ""}},
        "status": {"position": {"displayName": pos}, "thru": thru},
        "linescores": lines,
    }


golf_event = {
    "id": "401703510",
    "name": "Sanderson Farms Championship",
    "date": "2026-10-01T04:00Z",
    "endDate": "2026-10-04T04:00Z",
    "displayPurse": "$7,600,000",
    "status": status("in", "Round 2 - In Progress", "STATUS_IN_PROGRESS", 2),
    "competitions": [{
        "id": "401703510",
        "venue": venue("Country Club of Jackson", "Jackson", "MS"),
        "competitors": [
            golfer(1, "Ben Griffin", "1", "-11", [65], thru="14", today="-4"),
            golfer(2, "Taylor Pendrith", "T2", "-9", [66], thru="F", today="-3"),
            golfer(3, "Ryan Gerard", "T2", "-9", [68], thru="16", today="-5"),
            golfer(4, "Kevin Yu", "4", "-8", [67], thru="12", today="-3"),
            golfer(5, "Davis Thompson", "T5", "-7", [69], thru="F", today="-4"),
            golfer(6, "Mackenzie Hughes", "T5", "-7", [66], thru="10", today="-1"),
            golfer(7, "J.T. Poston", "T7", "-6", [70], thru="F", today="-4"),
            golfer(8, "Max Greyserman", "T7", "-6", [68], thru="15", today="-2"),
        ],
    }],
}
golf_cal = [
    {"id": "401703509", "label": "Procore Championship", "startDate": "2026-09-17T04:00Z", "endDate": "2026-09-20T04:00Z"},
    {"id": "401703510", "label": "Sanderson Farms Championship", "startDate": "2026-10-01T04:00Z", "endDate": "2026-10-04T04:00Z"},
    {"id": "401703511", "label": "Baycurrent Classic", "startDate": "2026-10-08T04:00Z", "endDate": "2026-10-11T04:00Z"},
    {"id": "401703512", "label": "Black Desert Championship", "startDate": "2026-10-22T04:00Z", "endDate": "2026-10-25T04:00Z"},
]
write("golf__pga__scoreboard.json", {"leagues": [{"abbreviation": "PGA", "calendar": golf_cal}], "events": [golf_event]})

# ── Standings ────────────────────────────────────────────────────────────────
def stat(abbr, value, name=None):
    return {"name": name or abbr.lower(), "abbreviation": abbr, "displayValue": str(value)}


def nfl_entry(abbr, w, l, pf, pa, div, strk):
    pct = f"{w / (w + l):.3f}".lstrip("0") if w + l else ".000"
    return {"team": {**TEAMS[abbr], "logos": [{"href": TEAMS[abbr]["logo"]}]}, "stats": [
        stat("W", w), stat("L", l), stat("T", 0), stat("PCT", pct), stat("PF", pf), stat("PA", pa),
        stat("DIFF", f"{pf - pa:+d}"), stat("DIV", div), stat("STRK", strk),
    ]}


write("football__nfl__standings.json", {"name": "National Football League", "children": [
    {"name": "National Football Conference", "children": [
        {"name": "NFC East", "standings": {"entries": [
            nfl_entry("PHI", 3, 1, 101, 74, "1-0", "L1"), nfl_entry("DAL", 3, 1, 109, 88, "1-0", "W2"),
            nfl_entry("WSH", 2, 2, 80, 82, "0-1", "W1"), nfl_entry("NYG", 1, 3, 61, 99, "0-1", "L2"),
        ]}},
        {"name": "NFC North", "standings": {"entries": [nfl_entry("GB", 2, 2, 90, 85, "1-1", "L1")]}},
    ]},
    {"name": "American Football Conference", "children": [
        {"name": "AFC East", "standings": {"entries": [nfl_entry("BUF", 4, 0, 120, 70, "1-0", "W4")]}},
        {"name": "AFC West", "standings": {"entries": [nfl_entry("KC", 3, 1, 98, 80, "1-0", "W1")]}},
    ]},
]})


def cfb_entry(abbr, conf, total, pf, pa, strk):
    return {"team": {**TEAMS[abbr], "logos": [{"href": TEAMS[abbr]["logo"]}]}, "stats": [
        {"name": "vsConf", "abbreviation": "CONF", "displayValue": conf},
        {"name": "overall", "abbreviation": "Total", "displayValue": total},
        stat("PF", pf, "pointsFor"), stat("PA", pa, "pointsAgainst"), stat("STRK", strk, "streak"),
    ]}


write("football__college-football__standings.json", {"children": [
    {"name": "Atlantic Coast Conference", "abbreviation": "ACC", "standings": {"entries": [
        cfb_entry("MIA", "2-0", "4-0", 160, 70, "W4"), cfb_entry("UVA", "1-0", "3-1", 128, 90, "W2"),
        cfb_entry("CLEM", "1-1", "2-2", 101, 95, "L1"), cfb_entry("LOU", "1-1", "3-1", 120, 88, "W1"),
        cfb_entry("UNC", "0-1", "2-2", 99, 104, "L1"), cfb_entry("DUKE", "0-1", "2-2", 92, 101, "L2"),
        cfb_entry("VT", "0-2", "1-3", 70, 120, "L3"),
    ]}},
    {"name": "Southeastern Conference", "abbreviation": "SEC", "standings": {"entries": [
        cfb_entry("UGA", "2-0", "4-0", 150, 60, "W4"), cfb_entry("BAMA", "1-0", "4-0", 155, 66, "W4"),
    ]}},
]})

write("basketball__mens-college-basketball__standings.json", {"children": []})


def epl_entry(abbr, gp, w, d, l, f, a):
    return {"team": {**TEAMS[abbr], "logos": [{"href": TEAMS[abbr]["logo"]}]}, "stats": [
        stat("GP", gp), stat("W", w), stat("D", d), stat("L", l), stat("F", f), stat("A", a),
        stat("GD", f"{f - a:+d}"), stat("P", 3 * w + d),
    ]}


write("soccer__eng.1__standings.json", {"children": [{"name": "English Premier League", "standings": {"entries": [
    epl_entry("ARS", 6, 5, 0, 1, 14, 4), epl_entry("MCI", 6, 4, 2, 0, 13, 5), epl_entry("LIV", 6, 4, 1, 1, 12, 6),
    epl_entry("NEW", 6, 4, 1, 1, 10, 6), epl_entry("CHE", 6, 3, 1, 2, 9, 8), epl_entry("TOT", 6, 2, 2, 2, 8, 8),
]}}]})

# ── Game summaries ───────────────────────────────────────────────────────────
def header_from(ev):
    comp = dict(ev["competitions"][0])
    comp.pop("venue", None)
    comp["competitors"] = [
        {**c, "record": [{"type": "total", "summary": c.get("records", [{}])[0].get("summary", "")}]}
        for c in comp["competitors"]
    ]
    return {"id": ev["id"], "competitions": [comp]}


def tstats(abbr, pairs):
    return {"team": TEAMS[abbr], "statistics": [{"name": k, "label": k, "displayValue": str(v)} for k, v in pairs]}


def athletes(rows):
    return [{"athlete": {"displayName": n, "shortName": n}, "stats": [str(s) for s in st]} for n, *st in rows]


nfl_summary = {
    "header": header_from(NFL_FINAL),
    "gameInfo": {
        "venue": venue("Lincoln Financial Field", "Philadelphia", "PA"),
        "attendance": 69879,
        "weather": {"temperature": 71, "displayValue": "Partly sunny"},
        "officials": [{"displayName": "Shawn Hochuli"}],
    },
    "pickcenter": [odds("PHI -3.5", 47.5, -3.5, -180, 150)],
    "boxscore": {
        "teams": [
            tstats("DAL", [("1st Downs", 22), ("Total Yards", 384), ("Passing", 268), ("Rushing", 116),
                           ("Turnovers", 0), ("3rd down efficiency", "6-12"), ("Possession", "32:14")]),
            tstats("PHI", [("1st Downs", 18), ("Total Yards", 321), ("Passing", 205), ("Rushing", 116),
                           ("Turnovers", 2), ("3rd down efficiency", "4-11"), ("Possession", "27:46")]),
        ],
        "players": [
            {"team": TEAMS["DAL"], "statistics": [
                {"name": "passing", "text": "Dallas Passing", "labels": ["C/ATT", "YDS", "TD", "INT", "QBR"],
                 "athletes": athletes([("D. Prescott", "24/33", 281, 2, 0, 78.4)]), "totals": ["24/33", "281", "2", "0", ""]},
                {"name": "rushing", "text": "Dallas Rushing", "labels": ["CAR", "YDS", "AVG", "TD", "LONG"],
                 "athletes": athletes([("J. Williams", 18, 88, 4.9, 1, 22), ("D. Prescott", 3, 12, 4.0, 0, 9)])},
                {"name": "receiving", "text": "Dallas Receiving", "labels": ["REC", "YDS", "AVG", "TD", "LONG"],
                 "athletes": athletes([("C. Lamb", 8, 121, 15.1, 1, 41), ("G. Pickens", 6, 84, 14.0, 1, 33)])},
            ]},
            {"team": TEAMS["PHI"], "statistics": [
                {"name": "passing", "text": "Philadelphia Passing", "labels": ["C/ATT", "YDS", "TD", "INT", "QBR"],
                 "athletes": athletes([("J. Hurts", "19/31", 214, 1, 1, 51.2)])},
                {"name": "rushing", "text": "Philadelphia Rushing", "labels": ["CAR", "YDS", "AVG", "TD", "LONG"],
                 "athletes": athletes([("S. Barkley", 21, 97, 4.6, 1, 19)])},
            ]},
        ],
    },
    "scoringPlays": [
        {"period": {"number": 1}, "clock": {"displayValue": "9:12"}, "team": {"id": "21"},
         "text": "Saquon Barkley 4 Yd Run (Jake Elliott Kick)", "awayScore": 0, "homeScore": 7},
        {"period": {"number": 1}, "clock": {"displayValue": "2:40"}, "team": {"id": "6"},
         "text": "Brandon Aubrey 54 Yd Field Goal", "awayScore": 3, "homeScore": 7},
        {"period": {"number": 2}, "clock": {"displayValue": "11:05"}, "team": {"id": "6"},
         "text": "CeeDee Lamb 41 Yd pass from Dak Prescott (Brandon Aubrey Kick)", "awayScore": 10, "homeScore": 7},
        {"period": {"number": 2}, "clock": {"displayValue": "0:31"}, "team": {"id": "6"},
         "text": "Javonte Williams 3 Yd Run (Brandon Aubrey Kick)", "awayScore": 17, "homeScore": 10},
        {"period": {"number": 4}, "clock": {"displayValue": "1:58"}, "team": {"id": "6"},
         "text": "George Pickens 18 Yd pass from Dak Prescott (Brandon Aubrey Kick)", "awayScore": 27, "homeScore": 20},
    ],
    "winprobability": [{"homeWinPercentage": p} for p in
                       [.62, .66, .70, .63, .55, .48, .40, .33, .38, .45, .52, .47, .41, .30, .22, .12, .05, .01]],
}
write("football__nfl__summary__401772001.json", nfl_summary)

# Upcoming games: summary has header + pickcenter only.
write("football__nfl__summary__401772045.json", {
    "header": header_from(NFL_DAL_NEXT),
    "gameInfo": {"venue": venue("AT&T Stadium", "Arlington", "TX")},
    "pickcenter": [odds("DAL -2.5", 49.5, -2.5, -142, 120),
                   odds("DAL -3", 49.0, -3.0, -150, 126, provider="DraftKings")],
})
write("football__college-football__summary__401755140.json", {
    "header": header_from(CFB_UVA),
    "gameInfo": {"venue": venue("Scott Stadium", "Charlottesville", "VA")},
    "pickcenter": [odds("UVA -3", 52.5, -3.0, -155, 130)],
})
write("soccer__eng.1__summary__740901.json", {
    "header": header_from(EPL_LIVE),
    "gameInfo": {"venue": venue("St James' Park", "Newcastle-upon-Tyne", country="England"), "attendance": 52123},
    "pickcenter": [odds("NEW +130", 2.5, None, 130, 210, draw_ml=240, provider="DraftKings")],
    "boxscore": {"teams": [
        tstats("CHE", [("Possession", "48.2"), ("Shots", 9), ("Shots on Goal", 3), ("Corner Kicks", 4), ("Fouls", 11)]),
        tstats("NEW", [("Possession", "51.8"), ("Shots", 12), ("Shots on Goal", 5), ("Corner Kicks", 6), ("Fouls", 9)]),
    ]},
    "keyEvents": [
        {"type": {"text": "Goal"}, "scoringPlay": True, "clock": {"displayValue": "23'"},
         "team": {"displayName": "Newcastle United"}, "text": "Goal! Alexander Isak (Newcastle) right footed shot."},
        {"type": {"text": "Yellow Card"}, "clock": {"displayValue": "38'"}, "team": {"displayName": "Chelsea"},
         "text": "Moisés Caicedo (Chelsea) is shown the yellow card."},
        {"type": {"text": "Goal"}, "scoringPlay": True, "clock": {"displayValue": "55'"},
         "team": {"displayName": "Chelsea"}, "text": "Goal! Cole Palmer (Chelsea) left footed shot from outside the box."},
        {"type": {"text": "Substitution"}, "clock": {"displayValue": "60'"}, "team": {"displayName": "Chelsea"},
         "text": "Substitution, Chelsea."},
    ],
})

# ── Team schedules (schedule endpoint shape: score objects, media.shortName) ─
def sched_event(eid, date, home, away, st, v, tv=None, hs=None, as_=None, hw=None):
    ev = event(eid, date, home, away, st, v)
    comp = ev["competitions"][0]
    comp["competitors"] = [
        competitor(home, "home", score=hs, winner=hw, schedule_shape=True),
        competitor(away, "away", score=as_, winner=None if hw is None else not hw, schedule_shape=True),
    ]
    comp["broadcasts"] = [{"media": {"shortName": tv}}] if tv else []
    return ev


FINAL = lambda: status("post", "Final", "STATUS_FINAL")  # noqa: E731
write("football__nfl__teams__6__schedule.json", {"team": TEAMS["DAL"], "events": [
    sched_event("401772010", "2026-09-20T20:25Z", "DAL", "NYG", FINAL(), venue("AT&T Stadium", "Arlington", "TX"), "FOX", 31, 17, True),
    sched_event("401772020", "2026-09-13T17:00Z", "WSH", "DAL", FINAL(), venue("Northwest Stadium", "Landover", "MD"), "FOX", 24, 21, True),
    sched_event("401772030", "2026-09-11T00:20Z", "DAL", "KC", FINAL(), venue("AT&T Stadium", "Arlington", "TX"), "NBC", 23, 20, True),
    sched_event("401772001", "2026-09-27T20:25Z", "PHI", "DAL", FINAL(), venue("Lincoln Financial Field", "Philadelphia", "PA"), "FOX", 20, 27, False),
    sched_event("401772045", "2026-10-04T20:25Z", "DAL", "GB", status("pre", "Sun, Oct 4"), venue("AT&T Stadium", "Arlington", "TX"), "CBS"),
    sched_event("401772060", "2026-10-12T00:15Z", "NYG", "DAL", status("pre", "Sun, Oct 11"), venue("MetLife Stadium", "East Rutherford", "NJ"), "ESPN"),
    sched_event("401772070", "2026-10-18T20:25Z", "DAL", "WSH", status("pre", "Sun, Oct 18"), venue("AT&T Stadium", "Arlington", "TX"), "FOX"),
]})
write("football__college-football__teams__258__schedule.json", {"team": TEAMS["UVA"], "events": [
    sched_event("401755110", "2026-09-05T23:00Z", "UVA", "COAST", FINAL(), venue("Scott Stadium", "Charlottesville", "VA"), "ACCN", 41, 13, True),
    sched_event("401755120", "2026-09-12T16:00Z", "CLEM", "UVA", FINAL(), venue("Memorial Stadium", "Clemson", "SC"), "ESPN", 28, 24, True),
    sched_event("401755130", "2026-09-26T20:00Z", "UVA", "DUKE", FINAL(), venue("Scott Stadium", "Charlottesville", "VA"), "ACCN", 34, 20, True),
    sched_event("401755140", "2026-10-03T19:30Z", "UVA", "UNC", status("pre", "Sat, Oct 3"), venue("Scott Stadium", "Charlottesville", "VA"), "ACCN"),
    sched_event("401755160", "2026-10-17T16:00Z", "LOU", "UVA", status("pre", "Sat, Oct 17"), venue("L&N Federal Credit Union Stadium", "Louisville", "KY"), "ESPN2"),
    sched_event("401755190", "2026-11-28T17:00Z", "VT", "UVA", status("pre", "Sat, Nov 28"), venue("Lane Stadium", "Blacksburg", "VA")),
]})
# A team that isn't in config.yaml, for the team page. The live feed's team block also
# carries color and standingSummary.
write("football__college-football__teams__61__schedule.json", {
    "team": {**TEAMS["UGA"], "color": "ba0c2f", "standingSummary": "1st in SEC"},
    "events": [
        sched_event("401755111", "2026-09-19T19:30Z", "UGA", "DUKE", FINAL(), venue("Sanford Stadium", "Athens", "GA"), "SEC Network", 38, 10, True),
        sched_event("401755150", "2026-10-03T23:30Z", "BAMA", "UGA", status("pre", "Sat, Oct 3"), venue("Bryant-Denny Stadium", "Tuscaloosa", "AL"), "ABC"),
    ],
})
write("basketball__mens-college-basketball__teams__258__schedule.json", {"team": TEAMS["UVA"], "events": [
    sched_event("401820001", "2026-11-03T23:00Z", "UVA", "COAST", status("pre", "Tue, Nov 3"), venue("John Paul Jones Arena", "Charlottesville", "VA"), "ACCNX"),
    sched_event("401820010", "2026-11-10T00:00Z", "UVA", "DUKE", status("pre", "Mon, Nov 9"), venue("John Paul Jones Arena", "Charlottesville", "VA"), "ESPN"),
]})

if __name__ == "__main__":
    print(f"Wrote {len(list(OUT.glob('*.json')))} fixtures to {OUT}")
