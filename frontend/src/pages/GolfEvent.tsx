import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { Leaderboard } from "../components/Golf";
import { ErrorBox, Skeleton } from "../components/QueryState";
import { golfQuery } from "../lib/api";
import { useSettings } from "../lib/settings";

export function GolfPage() {
  const { league = "", id = "" } = useParams();
  const { config } = useSettings();
  const query = useQuery({
    ...golfQuery(league, id),
    refetchInterval: (q) => (q.state.data?.state === "in" ? config.refresh_seconds * 1000 : false),
  });

  return (
    <div>
      <Link to="/" className="back">
        Back to scores
      </Link>
      {query.isPending ? (
        <Skeleton rows={10} />
      ) : query.isError ? (
        <ErrorBox error={query.error} retry={() => query.refetch()} />
      ) : (
        <Leaderboard t={query.data} />
      )}
    </div>
  );
}

export function NotFoundPage() {
  return (
    <div>
      <h1 className="page-title">Page not found</h1>
      <Link to="/" className="back">
        Go to scores
      </Link>
    </div>
  );
}
