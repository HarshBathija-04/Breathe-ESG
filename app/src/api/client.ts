/**
 * Axios client: API base URL from VITE_API_URL, JWT bearer auth, cold-start
 * tracking and a single place that reacts to expired sessions.
 */
import axios, { type InternalAxiosRequestConfig } from 'axios';
import { healthUrlFor } from '@/lib/http';
import { trackRequest } from '@/lib/wake';

export const API_BASE_URL: string = import.meta.env.VITE_API_URL || 'http://localhost:5110/api';
export const TOKEN_KEY = 'access_token';
export const USER_KEY = 'user';

type TrackedConfig = InternalAxiosRequestConfig & { _done?: () => void };

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 90_000, // generous: a sleeping Render instance can take ~60s to answer
});

apiClient.interceptors.request.use((config: TrackedConfig) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  config._done = trackRequest();
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    (response.config as TrackedConfig)._done?.();
    return response;
  },
  (error) => {
    (error.config as TrackedConfig | undefined)?._done?.();
    // Expired or invalid session: clear it and send the user to sign in again.
    if (error.response?.status === 401 && localStorage.getItem(TOKEN_KEY)) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      window.location.assign('/login?expired=1');
    }
    return Promise.reject(error);
  },
);

/** Fire-and-forget ping so a sleeping backend starts waking while the user reads. */
export function warmUpServer(): void {
  const done = trackRequest();
  fetch(healthUrlFor(API_BASE_URL))
    .catch(() => undefined)
    .finally(done);
}

export default apiClient;
