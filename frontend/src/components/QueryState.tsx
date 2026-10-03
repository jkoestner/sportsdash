import { ApiError } from "../lib/api";

/** Grey placeholder rows while a page's first request is in flight. */
export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="block skeleton" aria-busy="true" aria-label="Loading">
      <div className="sk-head" />
      {Array.from({ length: rows }, (_, i) => (
        <div className="sk-row" key={i}>
          <span />
          <span />
          <span />
        </div>
      ))}
    </div>
  );
}

export function ErrorBox({ error, retry }: { error: unknown; retry?: () => void }) {
  const msg =
    error instanceof ApiError
      ? error.message
      : "Couldn't reach the sportsdash server. Check that the backend is running.";
  return (
    <div className="block error-box" role="alert">
      <p>{msg}</p>
      {retry && (
        <button type="button" className="seg toggle" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
