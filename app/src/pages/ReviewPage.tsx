/*
Review queue - reviewers approve or reject normalized activities before audit lock.
*/
import { useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, ClipboardCheck, Eye, Loader2, Search, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { reviewApi, type NormalizedActivity, type ReviewDecision } from '@/api/review';
import {
  EmptyState,
  ErrorState,
  LoadMore,
  PageHeader,
  RoleNotice,
  ScopeBadge,
  StatusBadge,
} from '@/components/common';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/context/AuthContext';
import { formatCO2e, formatDate, formatNumber, humanize, sourceLabel } from '@/lib/format';
import { messageFromError } from '@/lib/http';

type Decision = 'APPROVE' | 'REJECT';
const FILTERS = [
  { value: '', label: 'All open' },
  { value: 'PENDING_REVIEW', label: 'Pending' },
  { value: 'FLAGGED', label: 'Flagged' },
];

export default function ReviewPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<NormalizedActivity[] | null>(null);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [loadingMore, setLoadingMore] = useState(false);
  const [decision, setDecision] = useState<{ activity: NormalizedActivity; type: Decision } | null>(null);
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [detail, setDetail] = useState<{
    activity: NormalizedActivity;
    history: ReviewDecision[] | null;
  } | null>(null);

  const load = useCallback(async (nextPage: number, filter: string) => {
    setError('');
    if (nextPage > 1) setLoadingMore(true);
    try {
      const data = await reviewApi.getPending({ page: nextPage, status: filter || undefined });
      setItems((prev) => (nextPage > 1 && prev ? [...prev, ...data.results] : data.results));
      setCount(data.count);
      setPage(nextPage);
    } catch (err) {
      setError(messageFromError(err, 'The review queue could not be loaded.'));
    } finally {
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    setItems(null);
    load(1, status);
  }, [load, status]);

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!items || !q) return items ?? [];
    return items.filter((a) =>
      [a.facility_code, a.vendor, a.sub_category, a.category, a.source_type].some((v) =>
        v?.toLowerCase().includes(q),
      ),
    );
  }, [items, search]);

  const submitDecision = async () => {
    if (!decision) return;
    setSubmitting(true);
    try {
      await reviewApi.submitDecision(decision.activity.id, decision.type, reason);
      setItems((prev) => prev?.filter((a) => a.id !== decision.activity.id) ?? null);
      setCount((c) => c - 1);
      toast.success(decision.type === 'APPROVE' ? 'Activity approved' : 'Activity rejected');
      setDecision(null);
      setReason('');
    } catch (err) {
      toast.error(messageFromError(err, 'The decision could not be saved.'));
    } finally {
      setSubmitting(false);
    }
  };

  const openDetail = async (activity: NormalizedActivity) => {
    setDetail({ activity, history: null });
    try {
      const data = await reviewApi.getHistory(activity.id);
      setDetail({ activity, history: data.decisions ?? [] });
    } catch (err) {
      toast.error(messageFromError(err, 'History could not be loaded.'));
      setDetail({ activity, history: [] });
    }
  };

  const actions = (a: NormalizedActivity) => (
    <div className="flex items-center justify-end gap-1">
      <Button
        size="sm"
        variant="ghost"
        className="text-success hover:bg-success-soft hover:text-success"
        disabled={!user?.can_review}
        onClick={() => setDecision({ activity: a, type: 'APPROVE' })}
        aria-label={`Approve ${a.sub_category} record`}
      >
        <CheckCircle2 aria-hidden="true" /> <span className="hidden xl:inline">Approve</span>
      </Button>
      <Button
        size="sm"
        variant="ghost"
        className="text-destructive hover:bg-danger-soft hover:text-destructive"
        disabled={!user?.can_review}
        onClick={() => setDecision({ activity: a, type: 'REJECT' })}
        aria-label={`Reject ${a.sub_category} record`}
      >
        <XCircle aria-hidden="true" /> <span className="hidden xl:inline">Reject</span>
      </Button>
      <Button
        size="icon-sm"
        variant="ghost"
        onClick={() => openDetail(a)}
        aria-label={`View details of ${a.sub_category} record`}
      >
        <Eye aria-hidden="true" />
      </Button>
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Review queue"
        description="Approve or reject normalized activities. Approved records can then be locked for audit."
      />

      {!user?.can_review && (
        <RoleNotice>
          Your {humanize(user?.role)} role can browse the queue but not decide. Sign in as the Reviewer demo
          account to approve or reject.
        </RoleNotice>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1 sm:max-w-sm">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            type="search"
            aria-label="Search loaded records"
            placeholder="Search facility, vendor, category"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-10 pl-9"
          />
        </div>
        <div
          role="group"
          aria-label="Filter by status"
          className="inline-flex w-fit rounded-lg border bg-card p-1"
        >
          {FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              aria-pressed={status === f.value}
              onClick={() => setStatus(f.value)}
              className="h-8 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors duration-150 hover:text-ink aria-pressed:bg-primary aria-pressed:text-primary-foreground"
            >
              {f.label}
            </button>
          ))}
        </div>
        <p className="tabular text-sm text-muted-foreground sm:ml-auto" aria-live="polite">
          {items ? `${count.toLocaleString()} open record${count === 1 ? '' : 's'}` : ''}
        </p>
      </div>

      <Card className="gap-0 overflow-hidden p-0">
        {error && !items ? (
          <ErrorState message={error} onRetry={() => load(1, status)} />
        ) : !items ? (
          <div className="space-y-3 p-5" aria-busy="true" aria-label="Loading review queue">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-11" />
            ))}
          </div>
        ) : visible.length === 0 ? (
          <EmptyState
            icon={ClipboardCheck}
            title={search ? `Nothing matches "${search.trim()}"` : 'Queue is clear'}
            description={
              search
                ? 'Search covers the records loaded so far. Try another term or load more first.'
                : 'Every record in this view has been reviewed. New uploads land here automatically.'
            }
            action={
              search ? (
                <Button variant="outline" onClick={() => setSearch('')}>
                  Clear search
                </Button>
              ) : undefined
            }
          />
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-sm">
                <caption className="sr-only">Activities awaiting review</caption>
                <thead className="border-b bg-secondary/60 text-left text-xs font-medium text-muted-foreground">
                  <tr>
                    <th scope="col" className="px-4 py-2.5 font-medium">
                      Source
                    </th>
                    <th scope="col" className="px-4 py-2.5 font-medium">
                      Scope
                    </th>
                    <th scope="col" className="px-4 py-2.5 font-medium">
                      Activity
                    </th>
                    <th scope="col" className="px-4 py-2.5 text-right font-medium">
                      Quantity
                    </th>
                    <th scope="col" className="px-4 py-2.5 text-right font-medium">
                      CO₂e
                    </th>
                    <th scope="col" className="px-4 py-2.5 font-medium">
                      Period
                    </th>
                    <th scope="col" className="px-4 py-2.5 font-medium">
                      Status
                    </th>
                    <th scope="col" className="px-4 py-2.5 text-right font-medium">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {visible.map((a) => (
                    <tr key={a.id} className="transition-colors duration-150 hover:bg-secondary/40">
                      <td className="px-4 py-2.5">
                        <span className="font-medium text-ink">{sourceLabel(a.source_type)}</span>
                        {a.facility_code && (
                          <span className="block text-xs text-muted-foreground">{a.facility_code}</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5">
                        <ScopeBadge scope={a.scope} />
                      </td>
                      <td className="px-4 py-2.5 text-ink">{humanize(a.sub_category)}</td>
                      <td className="tabular px-4 py-2.5 text-right text-ink">
                        {formatNumber(a.activity_value)}{' '}
                        <span className="text-muted-foreground">{a.normalized_unit}</span>
                      </td>
                      <td className="tabular px-4 py-2.5 text-right font-medium text-ink">
                        {formatCO2e(a.co2e)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-muted-foreground">
                        {formatDate(a.period_start, { month: 'short', year: 'numeric' })}
                      </td>
                      <td className="px-4 py-2.5">
                        <StatusBadge status={a.status} />
                      </td>
                      <td className="px-4 py-1.5">{actions(a)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <ul className="divide-y md:hidden">
              {visible.map((a) => (
                <li key={a.id} className="space-y-2 px-4 py-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-ink">{humanize(a.sub_category)}</p>
                      <p className="text-xs text-muted-foreground">
                        {sourceLabel(a.source_type)}
                        {a.facility_code && ` · ${a.facility_code}`} ·{' '}
                        {formatDate(a.period_start, { month: 'short', year: 'numeric' })}
                      </p>
                    </div>
                    <StatusBadge status={a.status} />
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-3 text-sm">
                      <ScopeBadge scope={a.scope} />
                      <span className="tabular font-medium text-ink">{formatCO2e(a.co2e)}</span>
                    </div>
                    {actions(a)}
                  </div>
                </li>
              ))}
            </ul>

            <LoadMore
              loaded={items.length}
              total={count}
              loading={loadingMore}
              onClick={() => load(page + 1, status)}
            />
          </>
        )}
      </Card>

      <Dialog open={!!decision} onOpenChange={(open) => !open && !submitting && setDecision(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{decision?.type === 'APPROVE' ? 'Approve activity' : 'Reject activity'}</DialogTitle>
            <DialogDescription>
              {decision &&
                `${humanize(decision.activity.sub_category)} · ${formatCO2e(decision.activity.co2e)} CO₂e · ${formatDate(decision.activity.period_start)}`}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="decision-reason">
              Reason {decision?.type === 'APPROVE' ? '(optional)' : '(required)'}
            </Label>
            <Textarea
              id="decision-reason"
              value={reason}
              maxLength={2000}
              onChange={(e) => setReason(e.target.value)}
              placeholder={
                decision?.type === 'APPROVE' ? 'Matches source invoice' : 'Why is this record rejected?'
              }
            />
            <p className="text-xs text-muted-foreground">The reason is stored in the audit trail.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDecision(null)} disabled={submitting}>
              Cancel
            </Button>
            <Button
              onClick={submitDecision}
              disabled={submitting || (decision?.type === 'REJECT' && !reason.trim())}
              variant={decision?.type === 'REJECT' ? 'destructive' : 'default'}
            >
              {submitting && <Loader2 className="animate-spin" aria-hidden="true" />}
              {decision?.type === 'APPROVE' ? 'Approve record' : 'Reject record'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!detail} onOpenChange={(open) => !open && setDetail(null)}>
        <DialogContent className="max-h-[85dvh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Activity detail</DialogTitle>
            <DialogDescription>
              {detail &&
                `${humanize(detail.activity.sub_category)} from ${sourceLabel(detail.activity.source_type)}`}
            </DialogDescription>
          </DialogHeader>
          {detail && (
            <div className="space-y-5 text-sm">
              <dl className="tabular grid grid-cols-2 gap-3">
                <div>
                  <dt className="text-xs text-muted-foreground">Quantity</dt>
                  <dd className="font-medium text-ink">
                    {formatNumber(detail.activity.activity_value)} {detail.activity.normalized_unit}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Emission factor</dt>
                  <dd className="font-medium text-ink">
                    {formatNumber(detail.activity.emission_factor, 4)} kg/{detail.activity.normalized_unit}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">CO₂e</dt>
                  <dd className="font-medium text-ink">{formatCO2e(detail.activity.co2e)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Factor source</dt>
                  <dd className="font-medium text-ink">{detail.activity.emission_factor_source || '-'}</dd>
                </div>
              </dl>
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Source row
                </h3>
                <pre className="mt-2 max-h-48 overflow-auto rounded-md border bg-secondary/50 p-3 font-mono text-xs">
                  {JSON.stringify(
                    detail.activity.source_payload?._raw ?? detail.activity.source_payload,
                    null,
                    2,
                  )}
                </pre>
              </section>
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Decisions
                </h3>
                {detail.history === null ? (
                  <Skeleton className="mt-2 h-12" />
                ) : detail.history.length === 0 ? (
                  <p className="mt-2 text-muted-foreground">No decisions recorded yet.</p>
                ) : (
                  <ul className="mt-2 space-y-2">
                    {detail.history.map((d) => (
                      <li key={d.id} className="rounded-md border p-3">
                        <div className="flex items-center justify-between gap-2">
                          <StatusBadge status={d.decision === 'APPROVE' ? 'APPROVED' : 'REJECTED'} />
                          <span className="text-xs text-muted-foreground">
                            {d.reviewed_by_name} · {formatDate(d.created_at)}
                          </span>
                        </div>
                        {d.reason && <p className="mt-2 text-foreground/90">{d.reason}</p>}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
