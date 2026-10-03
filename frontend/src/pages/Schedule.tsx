import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";
import { GameRow } from "../components/GameRow";
import { TournamentRow } from "../components/Golf";
import { ErrorBox, Skeleton } from "../components/QueryState";
import { Empty, Section } from "../components/Section";
import { scheduleQuery } from "../lib/api";
import { addDays, localDay, longDay } from "../lib/format";
import { byStart, isMyGame } from "../lib/games";
import { useSettings } from "../lib/settings";
import type { Game, Tournament } from "../types";

const RANGES = [3, 7, 14];

type Item = { kind: "game"; game: Game } | { kind: "golf"; t: Tournament };

export function SchedulePage() {
  const { config, tz, isEnabled } = useSettings();
  const [params] = useSearchParams();
  const days = RANGES.includes(Number(params.get("days"))) ? Number(params.get("days")) : config.schedule_days;
  const mineOnly = params.get("mine") === "1";
  const query = useQuery({ ...scheduleQuery(days), placeholderData: keepPreviousData });

  const href = (d: number, mine: boolean) => `/schedule?days=${d}${mine ? "&mine=1" : ""}`;

  let body;
  if (query.isPending) body = <Skeleton rows={6} />;
  else if (query.isError) body = <ErrorBox error={query.error} retry={() => query.refetch()} />;
  else {
    const { start } = query.data;
    // Bucket games (and golf events) by the calendar day they start on, in your timezone.
    const byDay = new Map<string, Item[]>();
    const add = (day: string, item: Item) => byDay.set(day, [...(byDay.get(day) ?? []), item]);

    for (const game of query.data.games) {
      if (!isEnabled(game.league) || (mineOnly && !isMyGame(game, config.teams))) continue;
      const day = localDay(game.start, tz);
      if (day) add(day, { kind: "game", game });
    }
    if (!mineOnly) {
      for (const t of query.data.tournaments) {
        if (!isEnabled(t.league)) continue;
        const day = localDay(t.start, tz) ?? start;
        add(day < start ? start : day, { kind: "golf", t }); // events already underway show on today
      }
    }

    const sorted = [...byDay.keys()].sort();
    body = sorted.length ? (
      sorted.map((day) => {
        const items = byDay.get(day)!.sort((a, b) => byStart(a.kind === "game" ? a.game : a.t, b.kind === "game" ? b.game : b.t));
        const title = day === start ? "Today" : day === addDays(start, 1) ? "Tomorrow" : longDay(day);
        const n = items.filter((i) => i.kind === "game").length;
        return (
          <Section key={day} title={title} count={n || undefined}>
            {items.map((i) =>
              i.kind === "game" ? (
                <GameRow key={i.game.id} game={i.game} showLeague />
              ) : (
                <TournamentRow key={i.t.id} t={i.t} leaders={0} showLeague />
              ),
            )}
          </Section>
        );
      })
    ) : (
      <Empty>Nothing scheduled in this window. Try a longer range or turn off “Your teams only”.</Empty>
    );
  }

  return (
    <div>
      <h1 className="page-title">Schedule</h1>
      <div className="controls">
        <div className="segmented" role="group" aria-label="Range">
          {RANGES.map((d) => (
            <Link key={d} to={href(d, mineOnly)} className={`seg${d === days ? " active" : ""}`}>
              {d} days
            </Link>
          ))}
        </div>
        <Link to={href(days, !mineOnly)} className={`seg toggle${mineOnly ? " active" : ""}`} aria-pressed={mineOnly}>
          Your teams only
        </Link>
      </div>
      <div className={query.isPlaceholderData ? "stale" : undefined}>{body}</div>
    </div>
  );
}
