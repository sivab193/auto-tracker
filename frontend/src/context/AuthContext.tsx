import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, setToken } from "../api/client";
import type { AuthConfig, User } from "../api/types";

interface AuthState {
  user: User | null;
  config: AuthConfig | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

interface TokenResponse {
  access_token: string;
  user: User;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    try {
      const me = await api.get<User>("/api/auth/me");
      setUser(me);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const cfg = await api.get<AuthConfig>("/api/auth/config");
        setConfig(cfg);
        // Single-user mode auto-authenticates; otherwise we need a token.
        if (cfg.single_user || localStorage.getItem("autotracker_token")) {
          await loadMe();
        }
      } catch {
        // API unreachable — leave unauthenticated.
      } finally {
        setLoading(false);
      }
    })();
  }, [loadMe]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<TokenResponse>("/api/auth/login", { email, password });
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const register = useCallback(async (email: string, name: string, password: string) => {
    const res = await api.post<TokenResponse>("/api/auth/register", { email, name, password });
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, config, loading, login, register, logout, refresh: loadMe }),
    [user, config, loading, login, register, logout, loadMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
