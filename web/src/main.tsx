import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
import "@/styles/globals.css";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "@/App";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Public read-only API: one retry is enough to absorb a cold start.
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("No se encontró el contenedor #root en index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
