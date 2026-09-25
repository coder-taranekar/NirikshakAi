/**
 * Mobile API client — Axios instance for the LabelGuard backend.
 *
 * API_URL resolution order:
 *   1. EXPO_PUBLIC_API_URL environment variable (set in .env)
 *   2. app.json extra.apiUrl
 *   3. Default: 10.0.2.2:8000 (Android emulator → host machine localhost)
 *
 * For a real device on the same network, set EXPO_PUBLIC_API_URL
 * to your machine's local IP, e.g. http://192.168.1.100:8000
 */

import axios from "axios";
import * as SecureStore from "expo-secure-store";
import Constants from "expo-constants";

const API_URL =
  process.env.EXPO_PUBLIC_API_URL ??
  Constants.expoConfig?.extra?.apiUrl ??
  "http://10.0.2.2:8000";

const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 120_000,
  headers: { "Content-Type": "application/json" },
});

// ── Attach JWT from SecureStore ───────────────────────────────────
apiClient.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Handle 401: attempt token refresh ────────────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refreshToken = await SecureStore.getItemAsync("refresh_token");
        if (!refreshToken) throw new Error("No refresh token");

        const { data } = await axios.post(`${API_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        await SecureStore.setItemAsync("access_token", data.access_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return apiClient(original);
      } catch {
        // Refresh failed — clear tokens and let the app handle redirect
        await SecureStore.deleteItemAsync("access_token");
        await SecureStore.deleteItemAsync("refresh_token");
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
