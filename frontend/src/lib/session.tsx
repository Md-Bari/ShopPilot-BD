"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError, getActiveBusinessId, setActiveBusinessId } from "./api/client";
import { authApi } from "./api/endpoints";
import type { Me, Membership } from "./types";

interface SessionValue {
  me: Me | null;
  loading: boolean;
  membership: Membership | null;
  refresh: () => Promise<Me | null>;
  selectBusiness: (businessId: number) => void;
  signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [businessId, setBusinessId] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await authApi.me();
      setMe(data);
      const stored = Number(getActiveBusinessId());
      const valid = data.memberships.find((m) => m.business_id === stored) ?? data.memberships[0] ?? null;
      setActiveBusinessId(valid ? valid.business_id : null);
      setBusinessId(valid ? valid.business_id : null);
      return data;
    } catch (err) {
      if (!(err instanceof ApiError) || err.status !== 401) console.error(err);
      setMe(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const selectBusiness = useCallback((id: number) => {
    setActiveBusinessId(id);
    setBusinessId(id);
  }, []);

  const signOut = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setActiveBusinessId(null);
      setMe(null);
      setBusinessId(null);
    }
  }, []);

  const membership = useMemo(
    () => me?.memberships.find((m) => m.business_id === businessId) ?? null,
    [me, businessId],
  );

  return (
    <SessionContext.Provider value={{ me, loading, membership, refresh, selectBusiness, signOut }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used inside SessionProvider");
  return ctx;
}

export function canManage(membership: Membership | null): boolean {
  return membership?.role === "owner" || membership?.role === "admin";
}
