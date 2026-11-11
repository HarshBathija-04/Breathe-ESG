/** Small, dependency-free helpers for talking to the API (unit-tested). */

export function healthUrlFor(apiBase: string): string {
  return `${apiBase.replace(/\/+$/, '').replace(/\/api$/, '')}/health`;
}

interface MaybeAxiosError {
  isAxiosError?: boolean;
  code?: string;
  response?: { status?: number; data?: { error?: unknown } };
}

/** Turn any thrown value into a sentence fit for a toast. */
export function messageFromError(err: unknown, fallback: string): string {
  const e = err as MaybeAxiosError | null;
  if (e && e.isAxiosError) {
    const apiMessage = e.response?.data?.error;
    if (typeof apiMessage === 'string' && apiMessage) return apiMessage;
    if (!e.response) {
      return e.code === 'ECONNABORTED'
        ? 'The server took too long to respond. Please try again.'
        : 'Could not reach the server. Check your connection and try again.';
    }
    if (e.response.status === 429) return 'Too many requests. Please wait a moment and try again.';
  }
  return fallback;
}
