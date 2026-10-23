"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

/** Гость на закрытой странице → на вход с возвратом обратно. */
export function useRequireAuth() {
  const auth = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (auth.status === "guest") router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [auth.status, pathname, router]);
  return auth;
}
