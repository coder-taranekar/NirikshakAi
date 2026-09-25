/**
 * Auth store — manages JWT token and current user in memory.
 * Persists to localStorage so the session survives page refresh.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      user: null,

      /** Called after a successful login API response */
      setAuth: ({ access_token, refresh_token, user }) => {
        set({ token: access_token, refreshToken: refresh_token, user });
      },

      /** Update the access token (e.g. after a refresh) */
      setToken: (token) => set({ token }),

      /** Clear auth state on logout */
      logout: () => set({ token: null, refreshToken: null, user: null }),

      /** Returns true if a token is present (does not validate expiry) */
      isAuthenticated: () => !!get().token,

      /** Returns true if the current user has the admin role */
      isAdmin: () => get().user?.role === "admin",
    }),
    {
      name: "labelguard-auth",   // localStorage key
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
    }
  )
);
