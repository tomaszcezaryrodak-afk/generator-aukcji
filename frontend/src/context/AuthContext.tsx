import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import { api } from '@/lib/api';

interface AuthState {
  token: string | null;
  sessionId: string | null;
  isAuthenticated: boolean;
  login: (password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    return sessionStorage.getItem('auth_token');
  });
  const [sessionId, setSessionId] = useState<string | null>(() => {
    return sessionStorage.getItem('session_id');
  });

  const login = useCallback(async (password: string) => {
    const res = await api.login(password);
    api.setToken(res.token);
    setToken(res.token);
    setSessionId(res.session_id);
    sessionStorage.setItem('auth_token', res.token);
    sessionStorage.setItem('session_id', res.session_id);
  }, []);

  const logout = useCallback(() => {
    api.setToken(null);
    setToken(null);
    setSessionId(null);
    sessionStorage.removeItem('auth_token');
    sessionStorage.removeItem('session_id');
  }, []);

  // Restore token to API client on mount
  if (token && !api.getToken()) {
    api.setToken(token);
  }

  // Auto-logout on 401
  useEffect(() => {
    api.setOnUnauthorized(logout);
    return () => api.setOnUnauthorized(null);
  }, [logout]);

  return (
    <AuthContext.Provider
      value={{
        token,
        sessionId,
        isAuthenticated: !!token,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}
