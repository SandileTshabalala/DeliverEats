import axios, { type InternalAxiosRequestConfig } from "axios";
import { refreshToken } from "./authService";

const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL,
  withCredentials: true, // important for cookies (refresh token)
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor to add access token to requests
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("access_token");
  if (token && config.headers) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

// Retry once on 401 after refreshing the token (avoids failed requests after idle)
let refreshPromise: Promise<string | null> | null = null;
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const config = err.config as InternalAxiosRequestConfig & { _retry?: boolean };
    if (err.response?.status !== 401 || config._retry) {
      return Promise.reject(err);
    }
    config._retry = true;
    if (!refreshPromise) {
      refreshPromise = refreshToken().then((data) => {
        refreshPromise = null;
        return data?.access_token ?? null;
      });
    }
    const newToken = await refreshPromise;
    if (newToken) {
      sessionStorage.setItem("access_token", newToken);
      if (config.headers) config.headers["Authorization"] = `Bearer ${newToken}`;
      return api.request(config);
    }
    return Promise.reject(err);
  }
);

export default api;
