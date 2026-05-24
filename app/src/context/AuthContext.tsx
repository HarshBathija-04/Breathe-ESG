/*

Auth context - provides authentication state to the entire app.
*/
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { authApi } from '@/api/auth';

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
  can_approve: boolean;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const storedUser = localStorage.getItem('user');
    const token = localStorage.getItem('access_token');

    if (storedUser && token) {
      try {
        const parsed = JSON.parse(storedUser);
        // Enhance with computed properties
        const enhanced = {
          ...parsed,
          can_review: ['admin', 'reviewer'].includes(parsed.role),
          can_approve: ['admin', 'reviewer'].includes(parsed.role),
        };
        setUser(enhanced);
      } catch {
        localStorage.removeItem('user');
        localStorage.removeItem('access_token');
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await authApi.login({ email, password });

    const enhancedUser: User = {
      ...response.user,
      full_name: `${response.user.first_name} ${response.user.last_name}`,
      can_review: ['admin', 'reviewer'].includes(response.user.role),
      can_approve: ['admin', 'reviewer'].includes(response.user.role),
    };

    localStorage.setItem('access_token', response.access);
    localStorage.setItem('user', JSON.stringify(enhancedUser));
    setUser(enhancedUser);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
