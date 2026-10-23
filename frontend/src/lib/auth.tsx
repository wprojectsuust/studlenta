"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, endpoints, onAuthLost, type Profile, type Token } from "@/lib/api";
import { clearGuestFavorites, readGuestFavorites } from "@/lib/guestFavorites";

type Status = "loading" | "guest" | "authenticated";
type AuthValue = {
  status: Status;
  user: Profile | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  reloadProfile: () => Promise<void>;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<Profile | null>(null);
  const [status, setStatus] = useState<Status>("loading");

  const becomeGuest = useCallback(() => {
    api.setAccessToken(null);
    setUser(null);
    setStatus("guest");
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        if (await api.refresh()) {
          const me = await endpoints.me();
          if (alive) {
            setUser(me);
            setStatus("authenticated");
          }
          return;
        }
      } catch {
        /* сессии нет или сервер недоступен — продолжаем как гость */
      }
      if (alive) setStatus("guest");
    })();
    const off = onAuthLost(() => {
      becomeGuest();
      void queryClient.invalidateQueries();
    });
    return () => {
      alive = false;
      off();
    };
  }, [becomeGuest, queryClient]);

  const signIn = useCallback(
    async (token: Token) => {
      api.setAccessToken(token.access_token);
      const guestFavorites = readGuestFavorites();
      if (guestFavorites.length) {
        try {
          await endpoints.syncFavorites(guestFavorites);
          clearGuestFavorites();
        } catch {
          /* не страшно: попробуем при следующем входе */
        }
      }
      setUser(await endpoints.me());
      setStatus("authenticated");
      await queryClient.invalidateQueries();
    },
    [queryClient],
  );

  const value = useMemo<AuthValue>(
    () => ({
      status,
      user,
      login: async (email, password) => signIn(await endpoints.login({ email, password })),
      register: async (email, password, fullName) =>
        signIn(await endpoints.register({ email, password, full_name: fullName })),
      logout: async () => {
        try {
          await endpoints.logout();
        } catch {
          /* выходим локально в любом случае */
        }
        becomeGuest();
        queryClient.removeQueries({ queryKey: ["me"] });
        await queryClient.invalidateQueries();
      },
      reloadProfile: async () => {
        if (status === "authenticated") setUser(await endpoints.me());
      },
    }),
    [status, user, signIn, becomeGuest, queryClient],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth вне AuthProvider");
  return value;
}
