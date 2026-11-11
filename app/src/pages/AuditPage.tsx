/*
Audit log - append-only timeline of every system action.
*/
import { useCallback, useEffect, useState } from 'react';
import {
  ArrowDownUp,
  CheckCircle2,
  ChevronDown,
  Edit3,
  Lock,
  ShieldCheck,
  TriangleAlert,
  Upload,
  type LucideIcon,
} from 'lucide-react';
import { auditApi, type AuditLogEntry } from '@/api/audit';
import { EmptyState, ErrorState, LoadMore, PageHeader } from '@/components/common';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDateTime, humanize } from '@/lib/format';
import { messageFromError } from '@/lib/http';
import { cn } from '@/lib/utils';

const ACTIONS: Record<string, { icon: LucideIcon; className: string }> = {
  INGEST: { icon: Upload, className: 'bg-info-soft text-info' },
  NORMALIZE: { icon: ArrowDownUp, className: 'bg-secondary text-secondary-foreground' },
  REVIEW: { icon: CheckCircle2, className: 'bg-success-soft text-success' },
  EDIT: { icon: Edit3, className: 'bg-warning-soft text-warning' },
  LOCK: { icon: Lock, className: 'bg-accent text-accent-foreground' },
  ANOMALY_FLAG: { icon: TriangleAlert, className: 'bg-danger-soft text-destructive' },
  ANOMALY_CLEAR: { icon: CheckCircle2, className: 'bg-secondary text-secondary-foreground' },
};

const FILTERS = ['', 'INGEST', 'REVIEW', 'LOCK', 'ANOMALY_FLAG', 'ANOMALY_CLEAR', 'EDIT'];

function Snapshot({ label, data }: { label: string; data: Record<string, unknown> }) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <pre className="mt-1 max-h-40 overflow-auto rounded-md border bg-card p-2 font-mono text-xs">
        {Object.keys(data).length ? JSON.stringify(data, null, 2) : '-'}
      </pre>
    </div>
  );
}

function Entry({ log }: { log: AuditLogEntry }) {
  const [open, setOpen] = useState(false);
  const meta = ACTIONS[log.action] ?? {
    icon: ShieldCheck,
    className: 'bg-secondary text-secondary-foreground',
  };
  return (
    <li>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-3 px-5 py-3 text-left transition-colors duration-150 hover:bg-secondary/50"
      >
        <span
          className={cn('mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md', meta.className)}
        >
          <meta.icon className="size-4" aria-hidden="true" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-baseline gap-x-2 text-sm">
            <span className="font-medium text-ink">{humanize(log.action)}</span>
            <span className="text-muted-foreground">
              {log.entity_type} <span className="font-mono text-xs">{log.entity_id.slice(0, 8)}</span>
            </span>
          </span>
          <span className="block truncate text-xs text-muted-foreground">
            {log.actor_name || 'System'}
            {log.reason && ` · ${log.reason}`}
          </span>
        </span>
        <span className="tabular hidden shrink-0 text-xs text-muted-foreground sm:block">
          {formatDateTime(log.timestamp)}
        </span>
        <ChevronDown
          className={cn(
            'mt-1 size-4 shrink-0 text-muted-foreground transition-transform duration-150',
            open && 'rotate-180',
          )}
          aria-hidden="true"
        />
      </button>
      {open && (
        <div className="space-y-3 border-t bg-secondary/40 px-5 py-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Snapshot label="Before" data={log.before} />
            <Snapshot label="After" data={log.after} />
          </div>
          <p className="break-all text-xs text-muted-foreground">
            {formatDateTime(log.timestamp)} · {log.actor_email || 'system'} · {log.entity_id}
          </p>
        </div>
      )}
    </li>
  );
}

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLogEntry[] | null>(null);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [action, setAction] = useState('');
  const [error, setError] = useState('');
  const [loadingMore, setLoadingMore] = useState(false);

  const load = useCallback(async (nextPage: number, filter: string) => {
    setError('');
    if (nextPage > 1) setLoadingMore(true);
    try {
      const data = await auditApi.getTimeline({ page: nextPage, action: filter || undefined });
      setLogs((prev) => (nextPage > 1 && prev ? [...prev, ...data.results] : data.results));
      setCount(data.count);
      setPage(nextPage);
    } catch (err) {
      setError(messageFromError(err, 'The audit log could not be loaded.'));
    } finally {
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    setLogs(null);
    load(1, action);
  }, [load, action]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit log"
        description="Append-only record of every ingest, decision, edit and lock, with before and after snapshots."
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <label htmlFor="action-filter" className="text-sm text-muted-foreground">
            Action
          </label>
          <select
            id="action-filter"
            value={action}
            onChange={(e) => setAction(e.target.value)}
            className="h-10 rounded-md border border-input bg-card px-3 text-sm transition-colors duration-150 hover:border-primary/60"
          >
            {FILTERS.map((f) => (
              <option key={f} value={f}>
                {f ? humanize(f) : 'All actions'}
              </option>
            ))}
          </select>
        </div>
        <p className="tabular text-sm text-muted-foreground" aria-live="polite">
          {logs ? `${count.toLocaleString()} entr${count === 1 ? 'y' : 'ies'}` : ''}
        </p>
      </div>

      <Card className="gap-0 overflow-hidden p-0">
        {error && !logs ? (
          <ErrorState message={error} onRetry={() => load(1, action)} />
        ) : !logs ? (
          <div className="space-y-3 p-5" aria-busy="true" aria-label="Loading audit log">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        ) : logs.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title={action ? `No ${humanize(action).toLowerCase()} entries yet` : 'No audit entries yet'}
            description="Entries appear here as soon as someone uploads, reviews, edits or locks a record."
          />
        ) : (
          <>
            <ul className="divide-y">
              {logs.map((log) => (
                <Entry key={log.id} log={log} />
              ))}
            </ul>
            <LoadMore
              loaded={logs.length}
              total={count}
              loading={loadingMore}
              onClick={() => load(page + 1, action)}
            />
          </>
        )}
      </Card>
    </div>
  );
}
