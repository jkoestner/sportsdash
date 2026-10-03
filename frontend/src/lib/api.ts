// Everything that talks to the backend lives here.
//
// Each `xxxQuery()` returns a TanStack Query "options" object: a cache key plus
// the function that fetches it. Components call `useQuery(scoresQuery(date))`;
// hover-prefetching calls `queryClient.prefetchQuery(scoresQuery(date))`. Same
// key, same cache entry, so a prefetched page renders instantly on click.

import { queryOptions } from "@tanstack/react-query";
import type {
  AppConfig,
  GameDetail,
  Playoffs,
  Poll,
  ScheduleResponse,
  ScoresResponse,
  StandingsResponse,
  TeamPanel,
  Tournament,
} from "../types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { Accept: "application/json" } });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* not JSON; keep the status text */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

const MINUTE = 60_000;

export const configQuery = () =>
  queryOptions({
    queryKey: ["config"],
    queryFn: () => get<AppConfig>("/api/config"),
    staleTime: 10 * MINUTE,
  });

export const scoresQuery = (date: string) =>
  queryOptions({
    queryKey: ["scores", date],
    queryFn: () => get<ScoresResponse>(`/api/scores?date=${date}`),
    staleTime: 20_000,
  });

export const scheduleQuery = (days: number) =>
  queryOptions({
    queryKey: ["schedule", days],
    queryFn: () => get<ScheduleResponse>(`/api/schedule?days=${days}`),
    staleTime: 5 * MINUTE,
  });

export const standingsQuery = (league: string) =>
  queryOptions({
    queryKey: ["standings", league],
    queryFn: () => get<StandingsResponse>(`/api/standings/${league}`),
    staleTime: 30 * MINUTE,
  });

export const teamsQuery = () =>
  queryOptions({
    queryKey: ["teams"],
    queryFn: () => get<TeamPanel[]>("/api/teams"),
    staleTime: 5 * MINUTE,
  });

export const teamQuery = (league: string, id: string) =>
  queryOptions({
    queryKey: ["team", league, id],
    queryFn: () => get<TeamPanel>(`/api/team/${league}/${id}`),
    staleTime: 5 * MINUTE,
    retry: (count, err) => !(err instanceof ApiError && err.status === 404) && count < 2,
  });

export const rankingsQuery = (league: string) =>
  queryOptions({
    queryKey: ["rankings", league],
    queryFn: () => get<Poll | null>(`/api/rankings/${league}`),
    staleTime: 30 * MINUTE,
  });

export const playoffsQuery = (league: string) =>
  queryOptions({
    queryKey: ["playoffs", league],
    queryFn: () => get<Playoffs | null>(`/api/playoffs/${league}`),
    staleTime: 60_000,
  });

export const gameQuery = (league: string, id: string) =>
  queryOptions({
    queryKey: ["game", league, id],
    queryFn: () => get<GameDetail>(`/api/game/${league}/${id}`),
    staleTime: 20_000,
    // 404 means ESPN hasn't published it; retrying won't help.
    retry: (count, err) => !(err instanceof ApiError && err.status === 404) && count < 2,
  });

export const golfQuery = (league: string, id: string) =>
  queryOptions({
    queryKey: ["golf", league, id],
    queryFn: () => get<Tournament>(`/api/golf/${league}/${id}`),
    staleTime: 20_000,
  });
