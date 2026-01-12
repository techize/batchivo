import axios, { type AxiosError, type InternalAxiosRequestConfig, type AxiosRequestConfig } from "axios";
import { getAuthTokens, setAuthTokens, isTokenExpired, clearAuthTokens } from "./auth";
import { config } from "./config";

// API base URL - supports runtime config (container env vars) with build-time fallback
const API_BASE_URL = config.apiUrl;

// Create axios instance with default config
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // Include cookies for auth
});

// Track if we're currently refreshing
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token!);
    }
  });

  failedQueue = [];
};

// Request interceptor (add auth token and handle refresh)
api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    // Skip auth for callback endpoint
    if (config.url?.includes('/auth/callback') || config.url?.includes('/auth/refresh')) {
      return config;
    }

    // Add authentication token if available
    const tokens = getAuthTokens();
    if (tokens) {

      // Check if token is expired or about to expire
      if (isTokenExpired(tokens) && !isRefreshing) {
        isRefreshing = true;

        try {
          // Attempt to refresh token
          const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: tokens.refreshToken,
          });

          const { access_token, refresh_token, expires_in } = response.data;
          const newTokens = {
            accessToken: access_token,
            refreshToken: refresh_token || tokens.refreshToken,
            expiresAt: Date.now() + expires_in * 1000,
          };

          setAuthTokens(newTokens);
          config.headers.Authorization = `Bearer ${access_token}`;
          processQueue(null, access_token);
        } catch (error) {
          processQueue(error, null);
          clearAuthTokens();
          window.location.href = '/login';
          return Promise.reject(error);
        } finally {
          isRefreshing = false;
        }
      } else if (isTokenExpired(tokens) && isRefreshing) {
        // Wait for refresh to complete
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          config.headers.Authorization = `Bearer ${token}`;
          return config;
        });
      } else {
        config.headers.Authorization = `Bearer ${tokens.accessToken}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor (handle errors globally)
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response) {
      // Server responded with error status
      console.error("API Error:", error.response.status, error.response.data);

      // Handle specific status codes
      if (error.response.status === 401) {
        // Unauthorized - clear tokens and redirect to login
        console.log("Unauthorized - redirecting to login");
        clearAuthTokens();
        window.location.href = '/login';
      }
    } else if (error.request) {
      // Request made but no response
      console.error("Network Error:", error.message);
    } else {
      // Something else happened
      console.error("Error:", error.message);
    }

    return Promise.reject(error);
  }
);

// API helper functions
export const apiClient = {
  // Generic GET request
  get: <T>(url: string, config?: AxiosRequestConfig) =>
    api.get<T>(url, config).then(res => res.data),

  // Generic POST request
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    api.post<T>(url, data, config).then(res => res.data),

  // Generic PUT request
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    api.put<T>(url, data, config).then(res => res.data),

  // Generic PATCH request
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    api.patch<T>(url, data, config).then(res => res.data),

  // Generic DELETE request
  delete: <T>(url: string, config?: AxiosRequestConfig) =>
    api.delete<T>(url, config).then(res => res.data),
};

// Health check endpoint
export const checkHealth = () => apiClient.get<{status: string; environment: string}>("/health");
