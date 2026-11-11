/**
 * Tracks requests slow enough to suggest a cold start (Render free instances
 * sleep after 15 idle minutes and need 30-60s to wake up).
 */
import { useSyncExternalStore } from 'react';

const SLOW_AFTER_MS = 4000;
let slowCount = 0;
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((listener) => listener());

/** Call when a request starts; returns a function to call once it settles. */
export function trackRequest(): () => void {
  let slow = false;
  let settled = false;
  const timer = window.setTimeout(() => {
    slow = true;
    slowCount += 1;
    emit();
  }, SLOW_AFTER_MS);
  return () => {
    if (settled) return;
    settled = true;
    window.clearTimeout(timer);
    if (slow) {
      slowCount -= 1;
      emit();
    }
  };
}

function subscribe(callback: () => void) {
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

export function useServerWaking(): boolean {
  return useSyncExternalStore(subscribe, () => slowCount > 0);
}
