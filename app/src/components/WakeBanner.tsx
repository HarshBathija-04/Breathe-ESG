/*
Shown while any request is unusually slow: the free-tier API is probably
waking up from sleep, which can take up to a minute.
*/
import { Loader2 } from 'lucide-react';
import { useServerWaking } from '@/lib/wake';

export function WakeBanner() {
  const waking = useServerWaking();
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 top-3 z-[60] flex justify-center px-4"
    >
      {waking && (
        <div className="pointer-events-auto flex max-w-md animate-fade-up items-start gap-3 rounded-lg border bg-card px-4 py-3 text-sm shadow-pop">
          <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin text-primary" aria-hidden="true" />
          <p>
            <span className="font-medium text-ink">Waking up the server.</span>{' '}
            <span className="text-muted-foreground">
              The demo API sleeps when idle and can take 30 to 60 seconds to start. Hang tight.
            </span>
          </p>
        </div>
      )}
    </div>
  );
}
