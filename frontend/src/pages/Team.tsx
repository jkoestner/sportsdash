import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router";
import { ErrorBox, Skeleton } from "../components/QueryState";
import { teamQuery } from "../lib/api";
import { TeamCard } from "./Teams";

/** Any team's page (/team/ncaaf/258): next game, then the season. Same card as "Your teams". */
export function TeamPage() {
  const { league = "", id = "" } = useParams();
  const query = useQuery(teamQuery(league, id));

  return (
    <div className="team-page">
      <BackButton />
      {query.isPending ? (
        <Skeleton rows={6} />
      ) : query.isError ? (
        <ErrorBox error={query.error} retry={() => query.refetch()} />
      ) : (
        <TeamCard panel={query.data} showLogo />
      )}
    </div>
  );
}

function BackButton() {
  // Teams are reached from game pages, the poll and standings, so go back to wherever that was.
  const navigate = useNavigate();
  return (
    <button
      type="button"
      className="back"
      // A page opened from a bookmark has nothing to go back to; React Router's history idx says so.
      onClick={() => ((window.history.state?.idx ?? 0) > 0 ? navigate(-1) : navigate("/"))}
    >
      Back
    </button>
  );
}
