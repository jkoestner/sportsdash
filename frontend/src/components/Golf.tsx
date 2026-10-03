import { Link } from "react-router";
import type { Tournament } from "../types";
import { dayRange } from "../lib/format";
import { location } from "../lib/games";
import { useSettings } from "../lib/settings";
import { Empty } from "./Section";

interface RowProps {
  t: Tournament;
  leaders?: number;
  showLeague?: boolean;
}

/** A tournament in a list of games: status, name, top of the leaderboard, course. */
export function TournamentRow({ t, leaders = 5, showLeague }: RowProps) {
  const { tz, leagueName } = useSettings();
  const span = dayRange(t.start, t.end, tz);
  const where = location(t);

  return (
    <Link to={`/golf/${t.league}/${t.id}`} className={`game tournament state-${t.state}`}>
      <div className="g-left">
        {t.state === "in" ? (
          <div className="g-status live">
            <span className="live-dot" />
            Live
          </div>
        ) : (
          <div className={`g-status${t.state === "post" ? " final" : ""}`}>{t.state === "post" ? "Final" : span}</div>
        )}
        {showLeague && <div className="g-league">{leagueName(t.league)}</div>}
      </div>
      <div className="g-teams">
        <div className="tour-name">{t.name}</div>
        <div className="tour-sub">
          {t.state !== "pre" && t.detail}
          {t.purse && <span className="purse">{t.purse}</span>}
        </div>
        {leaders > 0 && t.players.length > 0 && (
          <div className="leaderboard-mini">
            {t.players.slice(0, leaders).map((p, i) => (
              <div className="lb-row" key={`${p.name}-${i}`}>
                <span className="lb-pos">{p.pos}</span>
                <span className="lb-name">{p.name}</span>
                <span className="lb-score">{p.score}</span>
                <span className="lb-thru">{p.thru}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="g-odds" />
      <div className="g-meta">{where && <div className="g-venue">{where}</div>}</div>
    </Link>
  );
}

/** Full leaderboard table (golf page, PGA standings tab). */
export function Leaderboard({ t, limit }: { t: Tournament; limit?: number }) {
  const live = t.state === "in";
  const rounds = Math.max(0, ...t.players.map((p) => p.rounds.length));
  const players = limit ? t.players.slice(0, limit) : t.players;
  const sub = [t.detail, location(t), t.purse].filter(Boolean).join("   ");

  return (
    <section className="block">
      <div className="sec-head">
        <h2>{t.name}</h2>
        <span className="count">{sub}</span>
      </div>
      {players.length === 0 ? (
        <Empty>Tee times are posted the week of the event.</Empty>
      ) : (
        <div className="table-wrap">
          <table className="stats leaderboard">
            <thead>
              <tr>
                <th>Pos</th>
                <th>Player</th>
                <th>To par</th>
                {live && <th>Today</th>}
                {live && <th>Thru</th>}
                {Array.from({ length: rounds }, (_, i) => (
                  <th key={i}>R{i + 1}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {players.map((p, i) => (
                <tr key={`${p.name}-${i}`}>
                  <td>{p.pos}</td>
                  <td>{p.name}</td>
                  <td className="lb-total">{p.score}</td>
                  {live && <td>{p.today}</td>}
                  {live && <td>{p.thru}</td>}
                  {Array.from({ length: rounds }, (_, i) => (
                    <td key={i}>{p.rounds[i] ?? ""}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
