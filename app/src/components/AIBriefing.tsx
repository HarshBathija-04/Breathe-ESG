/*
AI emissions briefing: asks the backend (which calls Groq) to summarize the
tenant's reportable ledger. The browser never talks to the LLM directly.
*/
import { useState } from 'react';
import { AlertTriangle, Lightbulb, Loader2, RefreshCw, Sparkles, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';
import { dashboardApi, type Briefing } from '@/api/dashboard';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { messageFromError } from '@/lib/http';

const SECTIONS = [
  { key: 'highlights', title: 'Highlights', icon: TrendingUp, tone: 'text-primary' },
  { key: 'risks', title: 'Risks', icon: AlertTriangle, tone: 'text-warning' },
  { key: 'recommendations', title: 'Next steps', icon: Lightbulb, tone: 'text-info' },
] as const;

export function AIBriefing({ disabled }: { disabled?: boolean }) {
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const generate = async () => {
    setLoading(true);
    setError('');
    try {
      setBriefing(await dashboardApi.generateBriefing());
      toast.success('Briefing ready');
    } catch (err) {
      const message = messageFromError(err, 'The briefing could not be generated. Please try again.');
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="gap-0 overflow-hidden p-0">
      <div className="flex flex-col gap-3 border-b bg-accent/40 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Sparkles className="size-4" aria-hidden="true" />
          </div>
          <div>
            <h2 className="font-medium text-ink">AI emissions briefing</h2>
            <p className="text-sm text-muted-foreground">
              An executive summary of your reportable ledger, written by an LLM from aggregated numbers only.
            </p>
          </div>
        </div>
        <Button onClick={generate} disabled={loading || disabled} variant={briefing ? 'outline' : 'default'}>
          {loading ? (
            <Loader2 className="animate-spin" aria-hidden="true" />
          ) : briefing ? (
            <RefreshCw aria-hidden="true" />
          ) : (
            <Sparkles aria-hidden="true" />
          )}
          {loading ? 'Analyzing' : briefing ? 'Regenerate' : 'Generate briefing'}
        </Button>
      </div>

      <div className="px-5 py-5" aria-live="polite" aria-busy={loading}>
        {loading && (
          <div className="space-y-3" aria-label="Generating briefing">
            <div className="h-5 w-3/4 animate-pulse rounded bg-muted" />
            <div className="h-4 w-full animate-pulse rounded bg-muted" />
            <div className="h-4 w-5/6 animate-pulse rounded bg-muted" />
            <div className="grid gap-4 pt-2 md:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-24 animate-pulse rounded-lg bg-muted" />
              ))}
            </div>
          </div>
        )}

        {!loading && error && (
          <p role="alert" className="flex items-start gap-2 text-sm text-destructive">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            {error}
          </p>
        )}

        {!loading && !error && !briefing && (
          <p className="text-sm text-muted-foreground">
            {disabled
              ? 'Upload some activity data first, then generate a briefing.'
              : 'Generate a briefing to see emission hotspots, data-quality risks and recommended next steps.'}
          </p>
        )}

        {!loading && briefing && (
          <article className="animate-fade-up">
            <h3 className="font-display text-xl font-semibold tracking-tight text-ink">
              {briefing.headline}
            </h3>
            {briefing.summary && <p className="mt-2 text-sm text-foreground/90">{briefing.summary}</p>}
            <div className="mt-5 grid gap-5 md:grid-cols-3">
              {SECTIONS.map(({ key, title, icon: Icon, tone }) =>
                briefing[key].length ? (
                  <section key={key}>
                    <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      <Icon className={`size-3.5 ${tone}`} aria-hidden="true" />
                      {title}
                    </h4>
                    <ul className="mt-2 space-y-2">
                      {briefing[key].map((item, i) => (
                        <li key={i} className="border-l-2 pl-3 text-sm text-foreground/90">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </section>
                ) : null,
              )}
            </div>
            <p className="mt-5 text-xs text-muted-foreground">
              Generated by {briefing.model} on Groq from {briefing.context.record_count} reportable records.
              AI output can be wrong; verify figures against the ledger before sharing.
            </p>
          </article>
        )}
      </div>
    </Card>
  );
}
