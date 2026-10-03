import { Link } from "react-router";
import type { Game, Team } from "../types";
import { clock, localDay, shortDay } from "../lib/format";
import { isMyGame, isMyTeam, isOff, location } from "../lib/games";
import { useSettings } from "../lib/settings";
import { Logo } from "./Logo";
import { OddsLines } from "./Odds";

export function Status({ game }: { game: Game }) {
  const { tz } = useSettings();
  if (game.state === "in") {
    return (
      <div className="g-status live">
        <span className="live-dot" />
        {game.detail}
      </div>
    );
  }
  if (game.state === "post") return <div className="g-status final">{game.detail || "Final"}</div>;
  if (isOff(game)) return <div className="g-status final">{game.detail}</div>;
  return <div className="g-status">{game.time_valid ? clock(game.start, tz) : "TBD"}</div>;
}

function TeamLine({ team, game }: { team: Team; game: Game }) {
  const { config } = useSettings();
  const classes = ["t-line"];
  if (game.state === "post" && team.winner) classes.push("winner");
  if (isMyTeam(team, game.league, config.teams)) classes.push("mine");
  return (
    <div className={classes.join(" ")}>
      <Logo src={team.logo} abbr={team.abbr} />
      <span className="t-label">
        {team.rank && <span className="rank">{team.rank}</span>}
        <span className="t-name">{team.short || team.name}</span>
        {team.record && <span className="t-record">{team.record}</span>}
      </span>
      <span className="t-score">{game.state !== "pre" ? team.score : ""}</span>
    </div>
  );
}

interface Props {
  game: Game;
  showLeague?: boolean;
  showDate?: boolean;
}

/** One game: status, both teams, betting lines, venue/TV. The whole row links to the game page. */
export function GameRow({ game, showLeague, showDate }: Props) {
  const { config, tz, leagueName } = useSettings();
  const mine = isMyGame(game, config.teams);
  const day = localDay(game.start, tz);
  const where = location(game);

  return (
    <Link to={`/game/${game.league}/${game.id}`} className={`game state-${game.state}${mine ? " is-mine" : ""}`}>
      <div className="g-left">
        {showDate && day && <div className="g-date">{shortDay(day)}</div>}
        <Status game={game} />
        {showLeague && <div className="g-league">{leagueName(game.league)}</div>}
      </div>
      <div className="g-teams">
        <TeamLine team={game.away} game={game} />
        <TeamLine team={game.home} game={game} />
      </div>
      <OddsLines odds={game.odds} game={game} />
      <div className="g-meta">
        {game.note && <div className="g-note">{game.note}</div>}
        {where && <div className="g-venue">{where + (game.neutral ? " (neutral)" : "")}</div>}
        {game.broadcasts.length > 0 && <div className="g-tv">{game.broadcasts.join(", ")}</div>}
      </div>
    </Link>
  );
}
