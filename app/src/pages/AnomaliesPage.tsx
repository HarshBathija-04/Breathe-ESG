/*
Anomalies - data-quality flags raised by the pipeline, and their resolution.
*/
import { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, Loader2, ScanSearch } from 'lucide-react';
import { toast } from 'sonner';
import { anomalyApi, type AnomalyFlag, type AnomalyStats } from '@/api/anomaly';
import { EmptyState, ErrorState, PageHeader, ScopeBadge, StatusBadge } from '@/components/common';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/context/AuthContext';
import { formatCO2e, formatDate, humanize } from '@/lib/format';
import { messageFromError } from '@/lib/http';

const STATUS_FILTERS = ['OPEN', 'RESOLVED', 'CONFIRMED', 'IGNORED'];
const RESOLUTIONS = [
  {
    value: 'RESOLVED',
    label: 'Resolved',
    hint: 'The data is fine or was corrected. The record returns to the review queue.',
  },
  {
    value: 'CONFIRMED',
    label: 'Confirmed issue',
    hint: 'A real problem. The record stays flagged and out of totals.',
  },
  { value: 'IGNORED', label: 'Ignore', hint: 'Not relevant. The record returns to the review queue.' },
];

export default function AnomaliesPage() {
  const { user } = useAuth();
  const [status, setStatus] = useState('OPEN');
  const [flags, setFlags] = useState<AnomalyFlag[] | null>(null);
  const [count, setCount] = useState(0);
  const [stats, setStats] = useState<AnomalyStats | null>(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<AnomalyFlag | null>(null);
  const [resolution, setResolution] = useState('RESOLVED');
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async (filter: string) => {
    setError('');
    try {
      const [list, s] = await Promise.all([anomalyApi.list({ status: filter }), anomalyApi.getStats()]);
      setFlags(list.results);
      setCount(list.count);
      setStats(s);
    } catch (err) {
      setError(messageFromError(err, 'Anomalies could not be loaded.'));
    }
  }, []);

  useEffect(() => {
    setFlags(null);
    load(status);
  }, [load, status]);

  const resolve = async () => {
    if (!selected) return;
    setSubmitting(true);
    try {
      await anomalyApi.resolve(selected.id, resolution, note);
      setFlags((prev) => prev?.filter((f) => f.id !== selected.id) ?? null);
      setCount((c) => c - 1);
      toast.success(`Anomaly marked ${humanize(resolution).toLowerCase()}`);
      setSelected(null);
      setNote('');
      anomalyApi
        .getStats()
        .then(setStats)
        .catch(() => undefined);
    } catch (err) {
      toast.error(messageFromError(err, 'The anomaly could not be updated.'));
    } finally {
      setSubmitting(false);
    }
  };

  const byType = [...(stats?.by_type ?? [])].sort((a, b) => b.count - a.count);
  const maxType = Math.max(1, ...byType.map((t) => t.count));
  const statusCount = (s: string) => stats?.by_status.find((x) => x.status === s)?.count ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Anomalies"
        description="Flagged records are excluded from reportable totals until a reviewer resolves them."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="gap-4 self-start px-5 lg:sticky lg:top-6 lg:col-span-1">
          <h2 className="font-medium text-ink">By type</h2>
          {!stats ? (
            <Skeleton className="h-40" />
          ) : byType.length === 0 ? (
            <p className="text-sm text-muted-foreground">No anomalies detected.</p>
          ) : (
            <ul className="space-y-3">
              {byType.map((t) => (
                <li key={t.anomaly_type}>
                  <div className="flex justify-between text-sm">
                    <span className="text-ink">{humanize(t.anomaly_type)}</span>
                    <span className="tabular text-muted-foreground">{t.count}</span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden="true">
                    <div
                      className="h-full rounded-full bg-scope1"
                      style={{ width: `${(t.count / maxType) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="space-y-4 lg:col-span-2">
          <div role="group" aria-label="Filter by status" className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                type="button"
                aria-pressed={status === s}
                onClick={() => setStatus(s)}
                className="inline-flex h-9 items-center gap-2 rounded-full border bg-card px-3.5 text-sm font-medium text-muted-foreground transition-colors duration-150 hover:text-ink aria-pressed:border-primary aria-pressed:bg-primary aria-pressed:text-primary-foreground"
              >
                {humanize(s)}
                <span className="tabular text-xs opacity-80">{stats ? statusCount(s) : ''}</span>
              </button>
            ))}
          </div>

          <Card className="gap-0 overflow-hidden p-0">
            {error && !flags ? (
              <ErrorState message={error} onRetry={() => load(status)} />
            ) : !flags ? (
              <div className="space-y-3 p-5" aria-busy="true" aria-label="Loading anomalies">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-16" />
                ))}
              </div>
            ) : flags.length === 0 ? (
              <EmptyState
                icon={status === 'OPEN' ? CheckCircle2 : ScanSearch}
                title={
                  status === 'OPEN' ? 'No open anomalies' : `No ${humanize(status).toLowerCase()} anomalies`
                }
                description={
                  status === 'OPEN'
                    ? 'Every flag has been handled. New uploads are screened automatically.'
                    : undefined
                }
              />
            ) : (
              <ul className="divide-y">
                {flags.map((f) => (
                  <li key={f.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-start">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-ink">{humanize(f.anomaly_type)}</span>
                        <StatusBadge status={f.status} />
                        <span className="tabular text-xs text-muted-foreground">
                          {Math.round(Number(f.confidence) * 100)}% confidence
                        </span>
                      </div>
                      <p className="mt-1 break-words text-sm text-foreground/90">{f.description}</p>
                      <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                        <ScopeBadge scope={f.activity_details.scope} />
                        <span>{humanize(f.activity_details.sub_category)}</span>
                        <span className="tabular">{formatCO2e(f.activity_details.co2e)}</span>
                        <span>{formatDate(f.activity_details.period_start)}</span>
                      </p>
                      {f.resolution_note && (
                        <p className="mt-2 border-l-2 pl-3 text-xs text-muted-foreground">
                          {f.resolved_by_name}: {f.resolution_note}
                        </p>
                      )}
                    </div>
                    {f.status === 'OPEN' && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="self-start"
                        disabled={!user?.can_review}
                        title={
                          user?.can_review ? undefined : 'Only reviewers and admins can resolve anomalies'
                        }
                        onClick={() => {
                          setSelected(f);
                          setResolution('RESOLVED');
                        }}
                      >
                        Resolve
                      </Button>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {flags && flags.length < count && (
              <p className="border-t px-5 py-3 text-center text-xs text-muted-foreground">
                Showing the first {flags.length} of {count}.
              </p>
            )}
          </Card>
        </div>
      </div>

      <Dialog open={!!selected} onOpenChange={(open) => !open && !submitting && setSelected(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Resolve anomaly</DialogTitle>
            <DialogDescription>{selected?.description}</DialogDescription>
          </DialogHeader>
          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-medium text-ink">Outcome</legend>
            {RESOLUTIONS.map((r) => (
              <label
                key={r.value}
                className="flex cursor-pointer items-start gap-3 rounded-lg border p-3 has-[:checked]:border-primary has-[:checked]:bg-accent/50"
              >
                <input
                  type="radio"
                  name="resolution"
                  value={r.value}
                  checked={resolution === r.value}
                  onChange={() => setResolution(r.value)}
                  className="mt-1 accent-[hsl(var(--primary))]"
                />
                <span>
                  <span className="block text-sm font-medium text-ink">{r.label}</span>
                  <span className="block text-xs text-muted-foreground">{r.hint}</span>
                </span>
              </label>
            ))}
          </fieldset>
          <div className="space-y-1.5">
            <Label htmlFor="resolution-note">Note</Label>
            <Textarea
              id="resolution-note"
              value={note}
              maxLength={2000}
              onChange={(e) => setNote(e.target.value)}
              placeholder="What did you check?"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelected(null)} disabled={submitting}>
              Cancel
            </Button>
            <Button onClick={resolve} disabled={submitting}>
              {submitting && <Loader2 className="animate-spin" aria-hidden="true" />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
