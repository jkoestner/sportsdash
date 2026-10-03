import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";
import { Leaderboard } from "../components/Golf";
import { Logo } from "../components/Logo";
import { ErrorBox, Skeleton } from "../components/QueryState";
import { Empty } from "../components/Section";
import { standingsQuery } from "../lib/api";
import { useSettings } from "../lib/settings";
import type { StandingsGroup } from "../types";

export function StandingsPage() {
  const { config, enabled } = useSettings();
  const queryClient = useQueryClient();
  const [params] = useSearchParams();
  const leagues = enabled.length ? enabled : config.leagues;
  const current = leagues.find((l) => l.key === params.get("league")) ?? leagues[0]!;
  const query = useQuery(standingsQuery(current.key));
  const myIds = new Set(config.teams.filter((t) => t.leagues.includes(current.key)).map((t) => t.espn_id));

  let body;
  if (query.isPending) body = <Skeleton rows={8} />;
  else if (query.isError) body = <ErrorBox error={query.error} retry={() => query.refetch()} />;
  else if (current.kind === "golf")
    body = query.data.tournaments.length ? (
      query.data.tournaments.map((t) => <Leaderboard key={t.id} t={t} />)
    ) : (
      <Empty>No tournament on the {current.name} this week.</Empty>
    );
  else
    body = query.data.groups.length ? (
      query.data.groups.map((g) => <StandingsTable key={g.name} group={g} myIds={myIds} />)
    ) : (
      <Empty>{current.name} standings aren't published yet. They appear once the season starts.</Empty>
    );

  return (
    <div>
      <h1 className="page-title">Standings</h1>
      <div className="controls">
        <div className="segmented" role="tablist">
          {leagues.map((l) => (
            <Link
              key={l.key}
              to={`/standings?league=${l.key}`}
              role="tab"
              aria-selected={l.key === current.key}
              className={`seg${l.key === current.key ? " active" : ""}`}
              onPointerEnter={() => queryClient.prefetchQuery(standingsQuery(l.key))}
            >
              {l.name}
            </Link>
          ))}
        </div>
      </div>
      {body}
    </div>
  );
}

function StandingsTable({ group, myIds }: { group: StandingsGroup; myIds: Set<string> }) {
  return (
    <section className="block">
      <div className="sec-head">
        <h2>{group.name}</h2>
      </div>
      <div className="table-wrap">
        <table className="standings">
          <thead>
            <tr>
              <th className="st-team">Team</th>
              {group.columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {group.rows.map((r, i) => (
              <tr key={r.team_id || r.team} className={myIds.has(r.team_id) ? "mine" : undefined}>
                <td className="st-team">
                  <div className="st-team-in">
                    <span className="st-rank">{i + 1}</span>
                    <Logo src={r.logo} abbr={r.abbr} size="sm" />
                    <span>{r.team}</span>
                  </div>
                </td>
                {r.values.map((v, j) => (
                  <td key={j}>{v}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
