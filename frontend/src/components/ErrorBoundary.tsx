import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  /** Changing this (e.g. the URL) clears the error, so navigating away recovers. */
  resetKey?: string;
}

interface State {
  error: Error | null;
  stack: string;
}

/**
 * Without this, any error thrown while rendering unmounts the whole app and the
 * page goes blank (the error only appears in the browser console). This catches
 * it and shows the message in place of the broken part of the page.
 *
 * Error boundaries are the one thing React still requires a class component for.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, stack: "" };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("sportsdash render error:", error, info.componentStack);
    this.setState({ stack: info.componentStack ?? "" });
  }

  componentDidUpdate(prev: Props) {
    if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null, stack: "" });
  }

  render() {
    const { error, stack } = this.state;
    if (!error) return this.props.children;
    const details = `${error.name}: ${error.message}\n\nURL: ${window.location.href}\n${stack.trim()}`;
    return (
      <div className="block error-box crash" role="alert">
        <p>
          <strong>This page hit an error while rendering.</strong> The rest of the app still works; try another
          page or reload.
        </p>
        <pre>{details}</pre>
        <div className="crash-actions">
          <button type="button" className="seg toggle" onClick={() => window.location.reload()}>
            Reload
          </button>
          <button type="button" className="seg toggle" onClick={() => navigator.clipboard?.writeText(details)}>
            Copy error details
          </button>
        </div>
      </div>
    );
  }
}
