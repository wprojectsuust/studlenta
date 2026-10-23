import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { AuthProvider } from "@/lib/auth";

export function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
}

export function wrapper(client = makeClient()) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        <AuthProvider>{children}</AuthProvider>
      </QueryClientProvider>
    );
  };
}

export function renderWithProviders(ui: ReactElement, client = makeClient()) {
  return { client, ...render(ui, { wrapper: wrapper(client) }) };
}
