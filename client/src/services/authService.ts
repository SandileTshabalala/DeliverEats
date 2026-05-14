import api from "./api";
import type { Role } from "../utils/roles";

export interface User {
  id: string;
  email: string;
  name: string;
  sur_name: string;
  contact_number: string;
  role: Role;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const login = async (email: string, password: string): Promise<AuthResponse> => {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  const res = await api.post("/auth/login", formData, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  const { access_token, token_type, user } = res.data;

  // Save access token and user in session storage
  sessionStorage.setItem("access_token", access_token);
  sessionStorage.setItem("user", JSON.stringify(user));

  return { access_token, token_type, user };
};

export const refreshToken = async (): Promise<AuthResponse | null> => {
  try {
    const res = await api.post("/auth/refresh-access-token");
    const { access_token, user } = res.data;
    sessionStorage.setItem("access_token", access_token);
    if (user) sessionStorage.setItem("user", JSON.stringify(user));
    return res.data;
  } catch (err) {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("user");
    return null;
  }
};

export const logout = async (): Promise<void> => {
  try {
    await api.post("/auth/logout");
  } catch (err) {
    console.error("Logout failed", err);
  } finally {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("user");
  }
};

export const getCurrentUser = async (): Promise<User> => {
  const res = await api.get("/auth/me");
  return res.data;
};

export const register = async (userData: any): Promise<User> => {
  const res = await api.post("/auth/register", userData);
  return res.data;
};
