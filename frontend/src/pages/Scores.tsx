import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";
import { GameRow } from "../components/GameRow";
import { TournamentRow } from "../components/Golf";
import { ErrorBox, Skeleton } from "../components/QueryState";
import { Empty, Section } from "../components/Section";
import { scoresQuery } from "../lib/api";
import { addDays, clock, longDay, monthDay, shortDay, weekday } from "../lib/format";
import { groupBy, isMyGame, isRanked, sortLiveFirst } from "../lib/games";
import { useSettings } from "../lib/settings";
import type { ScoresResponse } from "../types";

export function ScoresPage() {
  const { config, tz, enabled } = useSettings();
  const [params] = useSearchParams();
  const today = config.today;
  const date = /^\d{4}-\d{2}-\d{2}$/.test(params.get("date") ?? "") ? params.get("date")! : today;
  const top25 = params.get("top25") === "1";
  // Leagues with a poll (config.yaml `rankings:`). The Top 25 filter only narrows these.
  const polled = enabled.filter((l) => l.rankings);

  // Only auto-refresh days that can have live games.
  const live = date === today || date === addDays(today, -1);
  const query = useQuery({
    ...scoresQuery(date),
    refetchInterval: live ? config.refresh_seconds * 1000 : false,
    placeholderData: keepPreviousData, // keep showing the old day while the new one loads
  });

  return (
    <div>
      <DayStrip today={today} selected={date} top25={top25} />
      <div className="title-row">
        <h1 className="page-title">{longDay(date)}</h1>
        {query.data && (
          <span className={`updated${query.isFetching ? " busy" : ""}`}>
            Updated {clock(new Date(query.dataUpdatedAt).toISOString(), tz)}
          </span>
        )}
      </div>
      {polled.length > 0 && (
        <div className="controls">
          <Link to={scoresHref(date, today, !top25)} className={`seg toggle${top25 ? " active" : ""}`} aria-pressed={top25}>
            {`${polled.map((l) => l.name).join(" / ")} Top 25 only`}
          </Link>
        </div>
      )}

      {query.isPending ? (
        <Skeleton rows={4} />
      ) : query.isError ? (
        <ErrorBox error={query.error} retry={() => query.refetch()} />
      ) : (
        <div className={query.isPlaceholderData ? "stale" : undefined}>
          <ScoresBody
            data={query.data}
            enabled={enabled.map((l) => l.key)}
            date={date}
            top25={top25 ? polled.map((l) => l.key) : []}
          />
        </div>
      )}
    </div>
  );
}

function scoresHref(date: string, today: string, top25: boolean): string {
  const q = new URLSearchParams();
  if (date !== today) q.set("date", date);
  if (top25) q.set("top25", "1");
  const qs = q.toString();
  return qs ? `/?${qs}` : "/";
}

function DayStrip({ today, selected, top25 }: { today: string; selected: string; top25: boolean }) {
  const queryClient = useQueryClient();
  const days = Array.from({ length: 8 }, (_, i) => addDays(today, i - 2));
  return (
    <nav className="day-strip" aria-label="Choose a day">
      {days.map((d) => (
        <Link
          key={d}
          to={scoresHref(d, today, top25)}
          className={`day${d === selected ? " active" : ""}`}
          aria-current={d === selected ? "date" : undefined}
          // Start loading on hover so the click feels instant.
          onPointerEnter={() => queryClient.prefetchQuery(scoresQuery(d))}
          onFocus={() => queryClient.prefetchQuery(scoresQuery(d))}
        >
          <span className="ds-dow">{d === today ? "Today" : weekday(d)}</span>
          <span className="ds-date">{monthDay(d)}</span>
        </Link>
      ))}
    </nav>
  );
}

function ScoresBody({
  data,
  enabled,
  date,
  top25,
}: {
  data: ScoresResponse;
  enabled: string[];
  date: string;
  top25: string[]; // leagues narrowed to games with a ranked team
}) {
  const { config } = useSettings();
  const games = data.games.filter((g) => enabled.includes(g.league));
  // Your teams stay pinned even when they're unranked.
  const mine = sortLiveFirst(games.filter((g) => isMyGame(g, config.teams)));
  const mineIds = new Set(mine.map((g) => g.id));
  const byLeague = groupBy(
    games.filter((g) => !mineIds.has(g.id) && (!top25.includes(g.league) || isRanked(g))),
    (g) => g.league,
  );
  const tours = groupBy(data.tournaments, (t) => t.league);

  const quiet: string[] = [];
  const sections = config.leagues
    .filter((lg) => enabled.includes(lg.key))
    .map((lg) => {
      if (lg.kind === "golf") {
        const list = tours.get(lg.key) ?? [];
        if (!list.length) {
          quiet.push(lg.name);
          return null;
        }
        return (
          <Section key={lg.key} title={lg.name}>
            {list.map((t) => (
              <TournamentRow key={t.id} t={t} />
            ))}
          </Section>
        );
      }
      const list = byLeague.get(lg.key) ?? [];
      const title = top25.includes(lg.key) ? `${lg.name} Top 25` : lg.name;
      if (!list.length) {
        if (!mine.some((g) => g.league === lg.key)) quiet.push(title);
        return null;
      }
      return (
        <Section key={lg.key} title={title} count={list.length}>
          {sortLiveFirst(list).map((g) => (
            <GameRow key={g.id} game={g} />
          ))}
        </Section>
      );
    });

  if (!enabled.length) return <Empty>Turn on a league above to see scores.</Empty>;

  return (
    <>
      {mine.length > 0 && (
        <Section title="Your teams" className="mine-block">
          {mine.map((g) => (
            <GameRow key={g.id} game={g} showLeague />
          ))}
        </Section>
      )}
      {sections}
      {quiet.length > 0 && (
        <p className="quiet">
          No games on {shortDay(date)}: {quiet.join(", ")}.
        </p>
      )}
    </>
  );
}
