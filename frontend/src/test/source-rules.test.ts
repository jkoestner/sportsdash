// Guards against mistakes that only show up in some browsers, so normal tests miss them.

import { expect, it } from "vitest";

// Vite loads every source file's text at test time (no Node APIs needed).
const sources = import.meta.glob<string>(["../**/*.{ts,tsx}", "!../test/**", "!../**/*.test.ts"], {
  query: "?raw",
  import: "default",
  eager: true,
});

it("finds the source files", () => {
  expect(Object.keys(sources)).toContain("../App.tsx");
});

it("effects never return a value by accident", () => {
  // `useEffect(() => something())` returns something() to React as the cleanup
  // function. When it isn't a function (newer Chrome's scrollTo returns a Promise),
  // React throws "destroy is not a function" and the page goes blank.
  // Write `useEffect(() => { something(); }, deps)` instead.
  const offenders = Object.entries(sources).flatMap(([file, text]) =>
    text
      .split("\n")
      .map((line, i) => ({ line, at: `${file}:${i + 1}` }))
      .filter(({ line }) => /use(Layout)?Effect\(\s*\(\)\s*=>\s*[^{\s]/.test(line))
      .map(({ at, line }) => `${at}  ${line.trim()}`),
  );
  expect(offenders).toEqual([]);
});
