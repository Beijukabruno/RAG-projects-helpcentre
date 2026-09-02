import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../lib/api';

interface User {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  project_ids: string[];
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, pass: string) => Promise<{ access_token: string; token_type: string; user: User }>;
  loginWithKeycloak: () => Promise<void>;
  completeLogin: (data: { access_token: string; token_type: string; user: User }) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (token) {
      fetchMe();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchMe = async () => {
    try {
      const resp = await api.get('/admin/auth/me');
      setUser(resp.data);
    } catch (err) {
      console.error('Failed to fetch user', err);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const persistAuth = (accessToken: string, userData: User) => {
    localStorage.setItem('admin_token', accessToken);
    setUser(userData);
  };

  const login = async (email: string, pass: string) => {
    const resp = await api.post('/admin/auth/login', { email, password: pass });
    const { access_token, user } = resp.data;
    persistAuth(access_token, user);
    return resp.data;
  };

  const loginWithKeycloak = async () => {
    const redirectUri = `${window.location.origin}/callback`;
    const resp = await api.get(`/admin/auth/keycloak/login?redirect_uri=${encodeURIComponent(redirectUri)}`);
    if (!resp.data?.url) {
      throw new Error('Keycloak login URL was not returned by the backend.');
    }
    window.location.assign(resp.data.url);
  };

  const completeLogin = (data: { access_token: string; token_type: string; user: User }) => {
    persistAuth(data.access_token, data.user);
  };

  const logout = () => {
    localStorage.removeItem('admin_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithKeycloak, completeLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
