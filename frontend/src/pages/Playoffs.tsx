import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";
import { GameRow } from "../components/GameRow";
import { Logo } from "../components/Logo";
import { ErrorBox, Skeleton } from "../components/QueryState";
import { Empty, Section } from "../components/Section";
import { playoffsQuery } from "../lib/api";
import { clock, localDay, longDay, shortDay } from "../lib/format";
import { groupBy, isMyTeam, sortLiveFirst } from "../lib/games";
import { useSettings } from "../lib/settings";
import type { Game, PlayoffSeries, Playoffs, SeriesTeam } from "../types";

export function PlayoffsPage() {
  const { config, enabled } = useSettings();
  const queryClient = useQueryClient();
  const [params] = useSearchParams();
  const withPlayoffs = (enabled.length ? enabled : config.leagues).filter((l) => l.playoffs);
  const leagues = withPlayoffs.length ? withPlayoffs : config.leagues.filter((l) => l.playoffs);
  const current = leagues.find((l) => l.key === params.get("league")) ?? leagues[0];
  const query = useQuery({ ...playoffsQuery(current?.key ?? ""), enabled: !!current });

  let body;
  if (!current) body = <Empty>None of your leagues have playoffs.</Empty>;
  else if (query.isPending) body = <Skeleton rows={6} />;
  else if (query.isError) body = <ErrorBox error={query.error} retry={() => query.refetch()} />;
  else if (!query.data) body = <Empty>ESPN doesn't publish a {current.name} postseason.</Empty>;
  else body = <PlayoffsView data={query.data} leagueName={current.name} />;

  return (
    <div>
      <h1 className="page-title">Playoffs</h1>
      {leagues.length > 0 && (
        <div className="controls">
          <div className="segmented" role="tablist">
            {leagues.map((l) => (
              <Link
                key={l.key}
                to={`/playoffs?league=${l.key}`}
                role="tab"
                aria-selected={l.key === current?.key}
                className={`seg${l.key === current?.key ? " active" : ""}`}
                onPointerEnter={() => queryClient.prefetchQuery(playoffsQuery(l.key))}
              >
                {l.name}
              </Link>
            ))}
          </div>
        </div>
      )}
      {body}
    </div>
  );
}

function PlayoffsView({ data, leagueName }: { data: Playoffs; leagueName: string }) {
  const { tz } = useSettings();
  const games = data.stages.flatMap((st) => st.series.flatMap((s) => s.games));
  // The bracket lists games weeks ahead (World Series vs TBD); "Up next" is the coming week.
  const soon = new Date(Date.now() + 7 * 86_400_000).toISOString();
  const upcoming = sortLiveFirst(
    [...games, ...data.other].filter((g) => g.state === "in" || (g.state === "pre" && !!g.start && g.start <= soon)),
  );
  const nextDay = localDay(data.next_start, tz);

  return (
    <>
      {nextDay && (
        <p className="po-note">
          {`The next ${leagueName} playoffs start ${longDay(nextDay)}. Here's how the ${data.season} postseason went.`}
        </p>
      )}
      {upcoming.length > 0 && (
        <Section title="Up next" count={upcoming.length}>
          {upcoming.map((g) => (
            <GameRow key={g.id} game={g} showDate />
          ))}
        </Section>
      )}

      {data.stages.length > 0 ? (
        <section className="block">
          <div className="sec-head">
            <h2>{data.season} bracket</h2>
          </div>
          <div className="bracket">
            {data.stages.map((st) => (
              <div className="br-col" key={st.name}>
                <h3 className="br-stage">{st.name}</h3>
                {[...groupBy(st.series, (s) => s.round)].map(([round, list]) => (
                  <div className="br-round" key={round}>
                    {/* Only label sub-rounds when a column mixes them (ALDS + NLDS). */}
                    {round !== st.name && <div className="br-round-name">{round}</div>}
                    {list.map((s) => (
                      <SeriesCard key={s.teams.map((t) => t.id).join("-") + s.round} series={s} />
                    ))}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </section>
      ) : (
        !nextDay && <Empty>The bracket fills in once the {leagueName} postseason starts.</Empty>
      )}
      {nextDay && data.stages.length === 0 && <Empty>No results from the {data.season} postseason.</Empty>}

      {data.other.length > 0 && (
        <Section title="Other postseason games" count={data.other.length}>
          {data.other.map((g) => (
            <GameRow key={g.id} game={g} showDate />
          ))}
        </Section>
      )}
    </>
  );
}

function SeriesCard({ series }: { series: PlayoffSeries }) {
  const single = series.best_of <= 1;
  const game = series.games[0];
  return (
    <div className={`br-series${series.completed ? " done" : ""}`}>
      {series.teams.map((t) => (
        <SeriesTeamLine key={t.id} team={t} series={series} single={single} />
      ))}
      <div className="br-foot">
        {!game ? (
          <div className="br-summary">Not scheduled yet</div>
        ) : single ? (
          <GameLink game={game} />
        ) : (
          <>
            <div className="br-summary">{series.summary || `Best of ${series.best_of}`}</div>
            <ol className="br-games">
              {series.games.map((g, i) => (
                <li key={g.id}>
                  <GameLink game={g} label={`G${i + 1}`} />
                </li>
              ))}
            </ol>
          </>
        )}
      </div>
    </div>
  );
}

function SeriesTeamLine({ team, series, single }: { team: SeriesTeam; series: PlayoffSeries; single: boolean }) {
  const { config } = useSettings();
  const league = series.games[0]?.league ?? "";
  const game = series.games[0];
  // A single game shows its score; a series shows wins.
  const side = game && (game.home.id === team.id ? game.home : game.away.id === team.id ? game.away : null);
  const started = series.games.some((g) => g.state !== "pre");
  const value = !started ? "" : single ? (side?.score ?? "") : String(team.wins);
  const loser = series.completed && !team.winner;
  const mine = isMyTeam(team, league, config.teams);
  return (
    <div className={`br-team${team.winner ? " winner" : ""}${loser ? " loser" : ""}${mine ? " mine" : ""}`}>
      <Logo src={team.logo} abbr={team.abbr} size="sm" />
      {team.rank && <span className="rank">{team.rank}</span>}
      {team.id && league ? (
        <Link to={`/team/${league}/${team.id}`} className="br-name">
          {team.short || team.name || "TBD"}
        </Link>
      ) : (
        <span className="br-name">{team.short || team.name || "TBD"}</span>
      )}
      <span className="br-wins">{value}</span>
    </div>
  );
}

function GameLink({ game, label }: { game: Game; label?: string }) {
  const { tz } = useSettings();
  const day = localDay(game.start, tz);
  let status: string;
  if (game.state === "in") status = game.detail || "Live";
  else if (game.state === "post") status = `${game.away.abbr} ${game.away.score}, ${game.home.abbr} ${game.home.score}`;
  else status = game.time_valid ? clock(game.start, tz) : "TBD";
  return (
    <Link to={`/game/${game.league}/${game.id}`} className={`br-game state-${game.state}`}>
      {label && <span className="br-g-label">{label}</span>}
      <span className="br-g-day">
        {day ? shortDay(day) : ""}
        {/if necessary/i.test(game.note) && game.state === "pre" && <span className="br-g-ifnec"> if needed</span>}
      </span>
      <span className="br-g-status">
        {game.state === "in" && <span className="live-dot" />}
        {status}
      </span>
    </Link>
  );
}
