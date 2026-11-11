/*
Auth context - JWT session state for the whole app.
*/
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { authApi, type AuthResponse } from '@/api/auth';
import { TOKEN_KEY, USER_KEY } from '@/api/client';

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: string;
  tenant: string;
  tenant_name: string;
  can_review: boolean;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function toUser(raw: AuthResponse['user']): User {
  return {
    ...raw,
    full_name: raw.full_name || `${raw.first_name} ${raw.last_name}`.trim(),
    can_review: ['admin', 'reviewer'].includes(raw.role),
  };
}

function readStoredUser(): User | null {
  try {
    const stored = localStorage.getItem(USER_KEY);
    if (stored && localStorage.getItem(TOKEN_KEY)) return toUser(JSON.parse(stored));
  } catch {
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(TOKEN_KEY);
  }
  return null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(readStoredUser);

  const login = useCallback(async (email: string, password: string) => {
    const response = await authApi.login({ email, password });
    localStorage.setItem(TOKEN_KEY, response.access);
    localStorage.setItem(USER_KEY, JSON.stringify(response.user));
    setUser(toUser(response.user));
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, isAuthenticated: !!user, login, logout }), [user, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}
