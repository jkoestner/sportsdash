import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import App from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import "./styles.css";

// One cache for the whole app. Data stays in memory for 10 minutes after a page
// stops using it, so going back to a page you just left is instant.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      gcTime: 10 * 60_000,
      refetchOnWindowFocus: true, // coming back to the tab refreshes stale data
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
