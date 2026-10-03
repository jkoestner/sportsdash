import { useQuery } from "@tanstack/react-query";
import type { CSSProperties } from "react";
import { Link } from "react-router";
import { GameRow } from "../components/GameRow";
import { Logo } from "../components/Logo";
import { OddsTable } from "../components/Odds";
import { ErrorBox, Skeleton } from "../components/QueryState";
import { Empty } from "../components/Section";
import { teamsQuery } from "../lib/api";
import { clock, localDay, shortDay } from "../lib/format";
import { hasLines, perspective } from "../lib/games";
import { useSettings } from "../lib/settings";
import type { Game, TeamPanel } from "../types";

export function TeamsPage() {
  const { isEnabled } = useSettings();
  const query = useQuery(teamsQuery());

  let body;
  if (query.isPending) body = <Skeleton rows={6} />;
  else if (query.isError) body = <ErrorBox error={query.error} retry={() => query.refetch()} />;
  else {
    const panels = query.data.filter((p) => isEnabled(p.league.key));
    body = panels.length ? (
      <div className="team-grid">
        {panels.map((p) => (
          <TeamCard key={`${p.team.espn_id}-${p.league.key}`} panel={p} />
        ))}
      </div>
    ) : (
      <Empty>Add teams under “teams:” in config.yaml, or turn their leagues back on above.</Empty>
    );
  }

  return (
    <div>
      <h1 className="page-title">Your teams</h1>
      {body}
    </div>
  );
}

/** A team's next game (with every book's line) and its season. Also the body of the single-team page. */
export function TeamCard({ panel, showLogo }: { panel: TeamPanel; showLogo?: boolean }) {
  const { team, league, next_game, next_odds, record, games, rank, standing } = panel;
  const ranked = rank ? `${(league.rankings || "").toUpperCase()} No. ${rank}`.trim() : "";
  // Fall back to the first book's line when the scoreboard didn't include one.
  const next: Game | null =
    next_game && !hasLines(next_game.odds) && next_odds[0] ? { ...next_game, odds: next_odds[0] } : next_game;

  return (
    // A CSS custom property set inline lets the stylesheet use each team's color.
    <section className="team-panel block" style={{ "--team": team.color } as CSSProperties}>
      <div className="tp-head">
        {showLogo ? <Logo src={panel.logo} abbr={team.short} size="lg" /> : <span className="tp-short">{team.short}</span>}
        <div>
          <h2>{team.name}</h2>
          <div className="tp-sub">{[league.name, record, standing, ranked].filter(Boolean).join(", ")}</div>
        </div>
      </div>

      {next && (
        <>
          <h3>Next game</h3>
          <GameRow game={next} showDate />
          {next_odds.length > 1 && <OddsTable odds={next_odds} game={next} />}
        </>
      )}

      <h3>Season</h3>
      <div className="team-sched">
        {games.length ? games.map((g) => <SeasonRow key={g.id} game={g} teamId={team.espn_id} />) : <Empty>Schedule not posted yet.</Empty>}
      </div>
    </section>
  );
}

function SeasonRow({ game, teamId }: { game: Game; teamId: string }) {
  const { tz } = useSettings();
  const { home, me, opp, won } = perspective(game, teamId);
  const day = localDay(game.start, tz);

  return (
    <Link to={`/game/${game.league}/${game.id}`} className={`ts-row${game.state !== "post" ? " upcoming" : ""}`}>
      <span className="ts-date">{day ? shortDay(day) : "TBD"}</span>
      <span className="ts-matchup">
        <span className="ts-at">{home ? "vs" : "at"}</span>
        <Logo src={opp.logo} abbr={opp.abbr} size="sm" />
        {opp.rank && <span className="rank">{opp.rank}</span>}
        <span className="ts-opp">{opp.short || opp.name}</span>
      </span>
      {won === null ? (
        <span className="res">{game.state === "in" ? "Live" : game.time_valid ? clock(game.start, tz) : "TBD"}</span>
      ) : (
        <span className={`res ${won ? "w" : "l"}`}>
          {won ? "W" : "L"} {me.score}-{opp.score}
        </span>
      )}
      <span className="ts-tv">{game.broadcasts.join(", ")}</span>
    </Link>
  );
}
