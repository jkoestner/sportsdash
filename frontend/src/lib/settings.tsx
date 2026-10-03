// App-wide settings shared through React context:
//   * the loaded config (timezone, leagues, your teams)
//   * which leagues are switched on in the header chips (remembered in localStorage)
//
// Any component can call `useSettings()` instead of passing these down as props.

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { AppConfig, LeagueInfo } from "../types";

const STORAGE_KEY = "sportsdash.hiddenLeagues";

interface Settings {
  config: AppConfig;
  tz: string;
  enabled: LeagueInfo[]; // in config order
  isEnabled: (key: string) => boolean;
  toggle: (key: string) => void;
  setAll: (on: boolean) => void;
  leagueName: (key: string) => string;
}

const SettingsContext = createContext<Settings | null>(null);

function readHidden(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return []; // private browsing or blocked storage: just show everything
  }
}

export function SettingsProvider({ config, children }: { config: AppConfig; children: ReactNode }) {
  // Store the *hidden* leagues, so a league newly added to config.yaml shows up by default.
  const [hidden, setHidden] = useState<string[]>(readHidden);

  const save = useCallback((next: string[]) => {
    setHidden(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* ignore */
    }
  }, []);

  const toggle = useCallback(
    (key: string) => save(hidden.includes(key) ? hidden.filter((k) => k !== key) : [...hidden, key]),
    [hidden, save],
  );

  const setAll = useCallback((on: boolean) => save(on ? [] : config.leagues.map((l) => l.key)), [config, save]);

  const value = useMemo<Settings>(() => {
    const names = new Map(config.leagues.map((l) => [l.key, l.name]));
    return {
      config,
      tz: config.timezone,
      enabled: config.leagues.filter((l) => !hidden.includes(l.key)),
      isEnabled: (key) => !hidden.includes(key),
      toggle,
      setAll,
      leagueName: (key) => names.get(key) ?? key.toUpperCase(),
    };
  }, [config, hidden, toggle, setAll]);

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): Settings {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error("useSettings must be used inside <SettingsProvider>");
  return ctx;
}
