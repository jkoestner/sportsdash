import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { Logo } from "../components/Logo";
import { OddsByBook } from "../components/Odds";
import { ErrorBox, Skeleton } from "../components/QueryState";
import { Empty, Section } from "../components/Section";
import { WinProbChart } from "../components/WinProbChart";
import { gameQuery, teamQuery } from "../lib/api";
import { clock, localDay, shortDay } from "../lib/format";
import { isMyTeam, location } from "../lib/games";
import { useSettings } from "../lib/settings";
import type { Game, GameDetail, PlayerTable, Situation, Team } from "../types";

export function GamePage() {
  const { league = "", id = "" } = useParams();
  const { config } = useSettings();
  const query = useQuery({
    ...gameQuery(league, id),
    // Keep polling only while the game is live.
    refetchInterval: (q) => (q.state.data?.game.state === "in" ? config.refresh_seconds * 1000 : false),
  });

  if (query.isPending) return <Skeleton rows={6} />;
  if (query.isError)
    return (
      <>
        <BackLink />
        <ErrorBox error={query.error} retry={() => query.refetch()} />
      </>
    );
  return <GameView detail={query.data} />;
}

function BackLink({ day }: { day?: string | null }) {
  return (
    <Link to={day ? `/?date=${day}` : "/"} className="back">
      Back to scores
    </Link>
  );
}

function periodLabel(sport: string, n: number): string {
  if (sport === "football") return n <= 4 ? String(n) : n === 5 ? "OT" : `${n - 4}OT`;
  if (sport === "basketball") return n <= 2 ? String(n) : n === 3 ? "OT" : `${n - 2}OT`;
  if (sport === "soccer") return n === 1 ? "1H" : n === 2 ? "2H" : `ET${n - 2}`;
  return String(n);
}

function GameView({ detail }: { detail: GameDetail }) {
  const { config, tz } = useSettings();
  const g = detail.game;
  const sport = config.leagues.find((l) => l.key === g.league)?.sport ?? "";
  const day = localDay(g.start, tz);

  const info: [string, string][] = [
    ["Venue", location(g) + (g.neutral ? " (neutral site)" : "")],
    ["Watch", g.broadcasts.join(", ")],
    ["Attendance", detail.attendance],
    ["Weather", detail.weather],
    ["Officials", detail.officials.slice(0, 3).join(", ")],
  ];

  return (
    <div>
      <BackLink day={day} />
      <Scoreboard game={g} />
      {g.state === "in" && detail.situation && <LiveSituation situation={detail.situation} game={g} />}
      <Linescore game={g} sport={sport} />

      <div className="detail-grid">
        <div className="detail-main">
          {detail.win_prob.length > 1 && (
            <Section title="Win probability">
              <WinProbChart points={detail.win_prob} homeAbbr={g.home.abbr} awayAbbr={g.away.abbr} live={g.state === "in"} />
            </Section>
          )}

          {detail.team_stats.length > 0 && (
            <Section title="Team stats">
              <table className="stats team-stats">
                <thead>
                  <tr>
                    <th>{g.away.abbr}</th>
                    <th />
                    <th>{g.home.abbr}</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.team_stats.map(([label, away, home], i) => (
                    <tr key={`${label}-${i}`}>
                      <td>{away}</td>
                      <td className="stat-label">{label}</td>
                      <td>{home}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Section>
          )}

          {detail.plays.length > 0 && (
            <Section title={sport === "soccer" ? "Key events" : "Scoring plays"}>
              <ol className="plays">
                {detail.plays.map((p, i) => (
                  <li className="play" key={i}>
                    <span className="pl-when">{[p.period, p.clock].filter(Boolean).join(" ")}</span>
                    <span className="pl-team">{p.team}</span>
                    <span className="pl-text">{p.text}</span>
                    <span className="pl-score">{p.score}</span>
                  </li>
                ))}
              </ol>
            </Section>
          )}

          {detail.player_tables.length > 0 && <PlayerStats tables={detail.player_tables} game={g} />}

          {!detail.team_stats.length && !detail.plays.length && !detail.player_tables.length && (
            <section className="block">
              <Empty>Stats appear here once the game starts.</Empty>
            </section>
          )}
        </div>

        <aside className="detail-side">
          <Section title="Game info">
            <dl className="info">
              {info
                .filter(([, v]) => v)
                .map(([k, v]) => (
                  <div key={k} className="info-row">
                    <dt>{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
            </dl>
          </Section>
          {detail.odds.length > 0 && (
            <Section title="Betting lines">
              <OddsByBook odds={detail.odds} game={g} />
            </Section>
          )}
        </aside>
      </div>
    </div>
  );
}

function Scoreboard({ game }: { game: Game }) {
  const { tz } = useSettings();
  const day = localDay(game.start, tz);
  const status =
    game.state === "pre" && game.start ? `${day ? shortDay(day) : ""}, ${clock(game.start, tz)}` : game.detail;

  return (
    <div className={`hero-board state-${game.state}`}>
      <BigTeam team={game.away} game={game} side="away" />
      <div className={`hb-status${game.state === "in" ? " live" : ""}`}>
        {game.state === "in" && <span className="live-dot" />}
        {status}
      </div>
      <BigTeam team={game.home} game={game} side="home" />
    </div>
  );
}

function BigTeam({ team, game, side }: { team: Team; game: Game; side: "home" | "away" }) {
  const { config } = useSettings();
  const queryClient = useQueryClient();
  const mine = isMyTeam(team, game.league, config.teams);
  const href = `/team/${game.league}/${team.id}`;
  const prefetch = () => queryClient.prefetchQuery(teamQuery(game.league, team.id));
  return (
    <div className={`hb-team ${side}${mine ? " mine" : ""}`}>
      <Link to={href} onPointerEnter={prefetch} tabIndex={-1} aria-hidden="true">
        <Logo src={team.logo} abbr={team.abbr} size="lg" />
      </Link>
      <div>
        <Link to={href} onPointerEnter={prefetch} onFocus={prefetch} className="hb-name" title={`${team.name} schedule`}>
          {team.rank && <span className="rank">{team.rank}</span>}
          {team.name}
        </Link>
        <div className="hb-record">{team.record}</div>
      </div>
      <div className={`hb-score${game.state === "post" && team.winner ? " winner" : ""}`}>
        {game.state !== "pre" ? team.score : ""}
      </div>
    </div>
  );
}

/** Down, distance and ball spot, drawn on a field with the away end zone on the left. */
function LiveSituation({ situation: s, game }: { situation: Situation; game: Game }) {
  const offense = s.possession === game.home.id ? game.home : s.possession === game.away.id ? game.away : null;
  const ytg = s.yards_to_endzone;
  // Home drives toward the left end zone, away toward the right. x is 0-100 from the left goal line.
  const toLeft = offense === game.home;
  const ball = offense && ytg !== null ? (toLeft ? ytg : 100 - ytg) : null;
  const goalToGo = s.distance !== null && ytg !== null && s.distance >= ytg;
  const firstDown = ball !== null && s.distance !== null && !goalToGo ? (toLeft ? ball - s.distance : ball + s.distance) : null;
  const spot = s.down_distance.split(" at ")[1] ?? "";

  return (
    <section className={`block situation${s.red_zone ? " red-zone" : ""}`} aria-label="Game situation">
      <div className="sit-head">
        {offense && (
          <div className="sit-poss">
            <Logo src={offense.logo} abbr={offense.abbr} />
            <span>
              <strong>{offense.abbr}</strong> ball
            </span>
          </div>
        )}
        {s.short_down_distance && (
          <div className="sit-down">
            {goalToGo ? s.short_down_distance.replace(/& \d+$/, "& Goal") : s.short_down_distance}
            {spot && <span className="sit-spot"> at {spot}</span>}
          </div>
        )}
        {s.red_zone && <span className="sit-badge">Red zone</span>}
      </div>

      <div className="field" role="img" aria-label={s.down_distance || "Field position"}>
        <div className="endzone">{game.away.abbr}</div>
        <div className="field-play">
          {[10, 20, 30, 40, 50, 60, 70, 80, 90].map((x) => (
            <span key={x} className="yard" style={{ left: `${x}%` }}>
              <span className="yard-num">{x <= 50 ? x : 100 - x}</span>
            </span>
          ))}
          {firstDown !== null && firstDown > 0 && firstDown < 100 && (
            <span className="first-down" style={{ left: `${firstDown}%` }} />
          )}
          {ball !== null && (
            <span className="ball" style={{ left: `${ball}%` }}>
              {toLeft ? "◀" : "▶"}
            </span>
          )}
        </div>
        <div className="endzone">{game.home.abbr}</div>
      </div>

      {(s.drive || s.last_play) && (
        <dl className="info sit-info">
          {s.drive && (
            <div className="info-row">
              <dt>Drive</dt>
              <dd>{s.drive}</dd>
            </div>
          )}
          {s.last_play && (
            <div className="info-row">
              <dt>Last play</dt>
              <dd>{s.last_play}</dd>
            </div>
          )}
        </dl>
      )}
    </section>
  );
}

/** Box score tables, one tab per team so you don't scroll past one team to reach the other. */
function PlayerStats({ tables, game }: { tables: PlayerTable[]; game: Game }) {
  const { config } = useSettings();
  const byTeam = new Map<string, PlayerTable[]>();
  for (const t of tables) byTeam.set(t.team, [...(byTeam.get(t.team) ?? []), t]);
  const teamFor = (key: string) => [game.away, game.home].find((t) => t.abbr === key || t.name === key);
  const keys = [...byTeam.keys()].sort((a, b) => (teamFor(a) === game.home ? 1 : 0) - (teamFor(b) === game.home ? 1 : 0));
  const mine = keys.find((k) => {
    const t = teamFor(k);
    return t && isMyTeam(t, game.league, config.teams);
  });
  const [picked, setPicked] = useState<string | null>(null);
  const active = picked && byTeam.has(picked) ? picked : (mine ?? keys[0]);

  return (
    <section className="block">
      <div className="sec-head">
        <h2>Player stats</h2>
      </div>
      <div className="team-tabs" role="tablist">
        {keys.map((k) => {
          const t = teamFor(k);
          return (
            <button
              key={k}
              type="button"
              role="tab"
              aria-selected={k === active}
              className={`team-tab${k === active ? " active" : ""}`}
              onClick={() => setPicked(k)}
            >
              {t && <Logo src={t.logo} abbr={t.abbr} size="sm" />}
              {t?.short || k}
            </button>
          );
        })}
      </div>
      <div role="tabpanel">
        {(byTeam.get(active ?? "") ?? []).map((t, ti) => (
          <div key={`${t.title}-${ti}`} className="box-group">
            <h3>{t.title}</h3>
            <div className="table-wrap">
              <table className="stats">
                <thead>
                  <tr>
                    <th>Player</th>
                    {t.labels.map((l) => (
                      <th key={l}>{l}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {t.rows.map((r, ri) => (
                    <tr key={ri}>
                      {r.map((v, j) => (
                        <td key={j}>{v}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Linescore({ game, sport }: { game: Game; sport: string }) {
  const n = Math.max(game.home.linescores.length, game.away.linescores.length);
  if (!n) return null;
  const cols = Array.from({ length: n }, (_, i) => i);
  return (
    <div className="table-wrap">
      <table className="linescore">
        <thead>
          <tr>
            <th />
            {cols.map((i) => (
              <th key={i}>{periodLabel(sport, i + 1)}</th>
            ))}
            <th>T</th>
          </tr>
        </thead>
        <tbody>
          {[game.away, game.home].map((t) => (
            <tr key={t.id}>
              <td className="ls-team">{t.abbr}</td>
              {cols.map((i) => (
                <td key={i}>{t.linescores[i] ?? ""}</td>
              ))}
              <td className="ls-total">{t.score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
