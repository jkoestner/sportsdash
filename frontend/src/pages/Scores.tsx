import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";
import { GameRow } from "../components/GameRow";
import { TournamentRow } from "../components/Golf";
import { ErrorBox, Skeleton } from "../components/QueryState";
import { Empty, Section } from "../components/Section";
import { scoresQuery } from "../lib/api";
import { addDays, clock, longDay, monthDay, shortDay, weekday } from "../lib/format";
import { groupBy, isMyGame, sortLiveFirst } from "../lib/games";
import { useSettings } from "../lib/settings";
import type { ScoresResponse } from "../types";

export function ScoresPage() {
  const { config, tz, enabled } = useSettings();
  const [params] = useSearchParams();
  const today = config.today;
  const date = /^\d{4}-\d{2}-\d{2}$/.test(params.get("date") ?? "") ? params.get("date")! : today;

  // Only auto-refresh days that can have live games.
  const live = date === today || date === addDays(today, -1);
  const query = useQuery({
    ...scoresQuery(date),
    refetchInterval: live ? config.refresh_seconds * 1000 : false,
    placeholderData: keepPreviousData, // keep showing the old day while the new one loads
  });

  return (
    <div>
      <DayStrip today={today} selected={date} />
      <div className="title-row">
        <h1 className="page-title">{longDay(date)}</h1>
        {query.data && (
          <span className={`updated${query.isFetching ? " busy" : ""}`}>
            Updated {clock(new Date(query.dataUpdatedAt).toISOString(), tz)}
          </span>
        )}
      </div>

      {query.isPending ? (
        <Skeleton rows={4} />
      ) : query.isError ? (
        <ErrorBox error={query.error} retry={() => query.refetch()} />
      ) : (
        <div className={query.isPlaceholderData ? "stale" : undefined}>
          <ScoresBody data={query.data} enabled={enabled.map((l) => l.key)} date={date} />
        </div>
      )}
    </div>
  );
}

function DayStrip({ today, selected }: { today: string; selected: string }) {
  const queryClient = useQueryClient();
  const days = Array.from({ length: 8 }, (_, i) => addDays(today, i - 2));
  return (
    <nav className="day-strip" aria-label="Choose a day">
      {days.map((d) => (
        <Link
          key={d}
          to={d === today ? "/" : `/?date=${d}`}
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
}: {
  data: ScoresResponse;
  enabled: string[];
  date: string;
}) {
  const { config } = useSettings();
  const games = data.games.filter((g) => enabled.includes(g.league));
  const mine = sortLiveFirst(games.filter((g) => isMyGame(g, config.teams)));
  const mineIds = new Set(mine.map((g) => g.id));
  const byLeague = groupBy(
    games.filter((g) => !mineIds.has(g.id)),
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
      if (!list.length) {
        if (!mine.some((g) => g.league === lg.key)) quiet.push(lg.name);
        return null;
      }
      return (
        <Section key={lg.key} title={lg.name} count={list.length}>
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
