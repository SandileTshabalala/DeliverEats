import React, { createContext, useState, useEffect, useContext } from "react";
import type { ReactNode } from "react";
import { login as loginService, refreshToken, logout as logoutService, getCurrentUser, register as registerService } from "../services/authService";
import type { AuthResponse, User } from "../services/authService";
// import { Role } from "../utils/roles"; // Role is in User now? Wait, User in authService has role as string.
// Let's keep logic simple for now.

// Remove local User interface



interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  loading: boolean;
  loginUser: (email: string, password: string) => Promise<AuthResponse>;
  registerUser: (userData: any) => Promise<User>;
  logoutUser: () => Promise<void>;
  reloadUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  user: null,
  loading: true,
  loginUser: async () => { throw new Error("Context not ready"); },
  registerUser: async () => { throw new Error("Context not ready"); },
  logoutUser: async () => { },
  reloadUser: async () => { },
});

interface Props {
  children: ReactNode;
}

import { jwtDecode } from "jwt-decode";

interface JWTPayload {
  sub: string;
  role: string;
  exp: number;
}

export const AuthProvider: React.FC<Props> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = sessionStorage.getItem("access_token");
      const cachedUser = sessionStorage.getItem("user");
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const decoded = jwtDecode<JWTPayload>(token);
        const now = Date.now() / 1000;
        if (decoded.exp <= now) {
          // Expired: try refresh without blocking UI
          setLoading(false);
          try {
            const refreshed = await refreshToken();
            if (refreshed) {
              setIsAuthenticated(true);
              setUser(refreshed.user ?? null);
            }
          } catch {
            setIsAuthenticated(false);
            setUser(null);
            sessionStorage.removeItem("access_token");
            sessionStorage.removeItem("user");
          }
          return;
        }
        // Valid token: show UI immediately with cache, then refresh user in background
        setIsAuthenticated(true);
        if (cachedUser) {
          try {
            setUser(JSON.parse(cachedUser));
          } catch {
            // ignore stale cache
          }
        }
        setLoading(false);
        const currentUser = await getCurrentUser();
        setUser(currentUser);
        sessionStorage.setItem("user", JSON.stringify(currentUser));
      } catch {
        setLoading(false);
        try {
          const refreshed = await refreshToken();
          if (refreshed) {
            setIsAuthenticated(true);
            setUser(refreshed.user ?? null);
          } else {
            setIsAuthenticated(false);
            setUser(null);
            sessionStorage.removeItem("access_token");
            sessionStorage.removeItem("user");
          }
        } catch {
          setIsAuthenticated(false);
          setUser(null);
          sessionStorage.removeItem("access_token");
          sessionStorage.removeItem("user");
        }
      }
    };

    initAuth();
  }, []);

  const loginUser = async (email: string, password: string): Promise<AuthResponse> => {
    try {
      const data: AuthResponse = await loginService(email, password);
      setIsAuthenticated(true);
      setUser(data.user);
      return data;
    } catch (err) {
      setIsAuthenticated(false);
      setUser(null);
      throw err;
    }
  };

  const logoutUser = async () => {
    try {
      // Call backend logout while token is still in sessionStorage
      await logoutService();
    } catch (err) {
      console.error("Background logout failed", err);
    } finally {
      // Always clear local state regardless of server response
      setIsAuthenticated(false);
      setUser(null);
      sessionStorage.removeItem("access_token");
      sessionStorage.removeItem("user");
    }
  };

  const registerUser = async (userData: any): Promise<User> => {
    try {
      const data = await registerService(userData);
      return data;
    } catch (err) {
      throw err;
    }
  };

  const reloadUser = async () => {
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      sessionStorage.setItem("user", JSON.stringify(currentUser));
    } catch (error) {
      console.error("Failed to reload user", error);
    }
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, loading, loginUser, logoutUser, registerUser, reloadUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
