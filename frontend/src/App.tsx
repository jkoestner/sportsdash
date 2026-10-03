import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link, NavLink, Outlet, Route, Routes, useLocation } from "react-router";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ErrorBox, Skeleton } from "./components/QueryState";
import { configQuery } from "./lib/api";
import { SettingsProvider, useSettings } from "./lib/settings";
import { GamePage } from "./pages/Game";
import { GolfPage, NotFoundPage } from "./pages/GolfEvent";
import { PlayoffsPage } from "./pages/Playoffs";
import { SchedulePage } from "./pages/Schedule";
import { ScoresPage } from "./pages/Scores";
import { StandingsPage } from "./pages/Standings";
import { TeamPage } from "./pages/Team";
import { TeamsPage } from "./pages/Teams";

export default function App() {
  // Everything else needs the config (timezone, leagues, your teams), so load it first.
  const config = useQuery(configQuery());

  if (config.isPending)
    return (
      <div className="shell">
        <Header />
        <main className="page">
          <Skeleton rows={4} />
        </main>
      </div>
    );
  if (config.isError)
    return (
      <div className="shell">
        <Header />
        <main className="page">
          <ErrorBox error={config.error} retry={() => config.refetch()} />
        </main>
      </div>
    );

  return (
    <SettingsProvider config={config.data}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<ScoresPage />} />
          <Route path="schedule" element={<SchedulePage />} />
          <Route path="standings" element={<StandingsPage />} />
          <Route path="playoffs" element={<PlayoffsPage />} />
          <Route path="teams" element={<TeamsPage />} />
          <Route path="team/:league/:id" element={<TeamPage />} />
          <Route path="game/:league/:id" element={<GamePage />} />
          <Route path="golf/:league/:id" element={<GolfPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </SettingsProvider>
  );
}

function Layout() {
  const { pathname, search } = useLocation();
  // New page starts at the top. The braces matter: whatever an effect returns, React
  // calls later as its cleanup. Newer browsers make scrollTo() return a Promise, so
  // `() => window.scrollTo(0, 0)` would hand React a Promise and crash the page.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="shell">
      <Header />
      <LeagueChips />
      {/* <Outlet /> renders whichever child <Route> matches the URL. */}
      <main className="page">
        <ErrorBoundary resetKey={pathname + search}>
          <Outlet />
        </ErrorBoundary>
      </main>
      <footer className="site-foot">Data from ESPN's public feeds.</footer>
    </div>
  );
}

const NAV = [
  { to: "/", label: "Scores" },
  { to: "/schedule", label: "Schedule" },
  { to: "/standings", label: "Standings" },
  { to: "/playoffs", label: "Playoffs" },
  { to: "/teams", label: "Your teams" },
];

function Header() {
  return (
    <header className="site-head">
      <div className="bar">
        <Link to="/" className="wordmark">
          sportsdash
        </Link>
        <nav className="nav" aria-label="Main">
          {NAV.map((n) => (
            // NavLink adds the "active" class automatically when the URL matches.
            <NavLink key={n.to} to={n.to} end={n.to === "/"} className="nav-link">
              {n.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}

function LeagueChips() {
  const { config, enabled, isEnabled, toggle, setAll } = useSettings();
  return (
    <fieldset className="league-chips">
      <legend className="sr-only">Leagues to show</legend>
      {config.leagues.map((l) => (
        <label key={l.key} className={isEnabled(l.key) ? "on" : undefined}>
          <input type="checkbox" checked={isEnabled(l.key)} onChange={() => toggle(l.key)} />
          {l.name}
        </label>
      ))}
      <span className="chip-bulk">
        <button type="button" onClick={() => setAll(true)} disabled={enabled.length === config.leagues.length}>
          Select all
        </button>
        <button type="button" onClick={() => setAll(false)} disabled={enabled.length === 0}>
          Deselect all
        </button>
      </span>
    </fieldset>
  );
}
