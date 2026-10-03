import type { Game, Odds } from "../types";
import { hasLines } from "../lib/games";

function Line({ label, value }: { label: string; value: string }) {
  return (
    <div className="odd">
      <span className="o-label">{label}</span>
      <span className="o-value">{value}</span>
    </div>
  );
}

function moneyline(o: Odds, game: Game, homeFirst: boolean): string {
  const away = `${game.away.abbr} ${o.away_ml}`;
  const home = `${game.home.abbr} ${o.home_ml}`;
  const draw = o.draw_ml ? `Draw ${o.draw_ml}` : "";
  return (homeFirst ? [home, draw, away] : [away, draw, home]).filter(Boolean).join("  ");
}

/** Spread / moneyline / total for one sportsbook. Soccer shows the three-way moneyline instead of a spread. */
export function OddsLines({ odds, game }: { odds: Odds | null | undefined; game: Game }) {
  if (!hasLines(odds)) return <div className="g-odds" />;
  const soccer = !!odds.draw_ml;
  return (
    <div className="g-odds" title={odds.provider}>
      {!soccer && odds.details && <Line label="Spread" value={odds.details} />}
      {(odds.away_ml || odds.home_ml) && <Line label="Moneyline" value={moneyline(odds, game, soccer)} />}
      {odds.over_under != null && <Line label="Total" value={`O/U ${odds.over_under}`} />}
    </div>
  );
}

/** Every sportsbook ESPN lists, stacked (game page sidebar). */
export function OddsByBook({ odds, game }: { odds: Odds[]; game: Game }) {
  return (
    <div>
      {odds.map((o) => (
        <div className="book" key={o.provider || o.details}>
          <div className="book-name">{o.provider || "Line"}</div>
          {o.details && !o.draw_ml && <Line label="Spread" value={o.details} />}
          {o.over_under != null && <Line label="Total" value={`O/U ${o.over_under}`} />}
          {(o.away_ml || o.home_ml) && <Line label="Moneyline" value={moneyline(o, game, false)} />}
        </div>
      ))}
    </div>
  );
}

/** Side-by-side comparison table (Your teams page). */
export function OddsTable({ odds, game }: { odds: Odds[]; game: Game }) {
  const draw = odds.some((o) => o.draw_ml);
  return (
    <div className="table-wrap">
      <table className="stats odds-table">
        <thead>
          <tr>
            <th>Book</th>
            <th>Spread</th>
            <th>Total</th>
            <th>{game.away.abbr} ML</th>
            {draw && <th>Draw</th>}
            <th>{game.home.abbr} ML</th>
          </tr>
        </thead>
        <tbody>
          {odds.map((o) => (
            <tr key={o.provider}>
              <td>{o.provider}</td>
              <td>{o.details}</td>
              <td>{o.over_under ?? ""}</td>
              <td>{o.away_ml}</td>
              {draw && <td>{o.draw_ml}</td>}
              <td>{o.home_ml}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
