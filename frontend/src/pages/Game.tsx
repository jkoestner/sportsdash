import { useQuery, useQueryClient } from "@tanstack/react-query";
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
import type { Game, GameDetail, Team } from "../types";

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

          {detail.player_tables.map((t, ti) => (
            <Section key={`${t.team}-${t.title}-${ti}`} title={t.team && !t.title.includes(" ") ? `${t.team} ${t.title}` : t.title}>
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
            </Section>
          ))}

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
