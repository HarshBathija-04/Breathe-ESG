/*
Dashboard - reportable emissions, pipeline status and the AI briefing.
*/
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Fuel, Plane, Upload, Zap, type LucideIcon } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { dashboardApi, type DashboardStats, type ScopeKey } from '@/api/dashboard';
import { AIBriefing } from '@/components/AIBriefing';
import { EmptyState, ErrorState, PageHeader, StatusBadge } from '@/components/common';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { formatCO2e, formatDate, formatMonth, scopeLabel, sourceLabel } from '@/lib/format';
import { messageFromError } from '@/lib/http';
import { CHART_GRID, CHART_TEXT, SCOPE_COLORS } from '@/lib/theme';

const SCOPES: ScopeKey[] = ['Scope1', 'Scope2', 'Scope3'];
const CATEGORY_ICONS: Record<string, LucideIcon> = { fuel: Fuel, electricity: Zap, travel: Plane };

function Kpi({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: string }) {
  return (
    <div className="bg-card p-4 sm:p-5">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className={`tabular mt-1 text-2xl font-semibold tracking-tight ${tone ?? 'text-ink'}`}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading dashboard">
      <Skeleton className="h-9 w-56" />
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-none" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <Skeleton className="h-80 rounded-xl lg:col-span-2" />
        <Skeleton className="h-80 rounded-xl" />
      </div>
    </div>
  );
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string; value: number }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-pop">
      <p className="mb-1 font-medium text-ink">{label ? formatMonth(label) : ''}</p>
      {payload.map((p) => (
        <p key={p.dataKey} className="tabular flex items-center gap-2 text-muted-foreground">
          <span className="size-2 rounded-full" style={{ background: SCOPE_COLORS[p.dataKey as ScopeKey] }} />
          {scopeLabel(p.dataKey)}: <span className="font-medium text-ink">{formatCO2e(p.value)}</span>
        </p>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState('');

  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    dashboardApi
      .getStats()
      .then((data) => {
        setStats(data);
        setError('');
      })
      .catch((err) => setError(messageFromError(err, 'The dashboard could not be loaded.')));
  }, [attempt]);

  const retry = () => {
    setError('');
    setAttempt((n) => n + 1);
  };

  if (error && !stats) return <ErrorState message={error} onRetry={retry} />;
  if (!stats) return <DashboardSkeleton />;

  const a = stats.activities;
  const reportable = stats.emissions_by_scope.reduce((sum, s) => sum + Number(s.total_co2e || 0), 0);
  const byScope = SCOPES.map((scope) => {
    const row = stats.emissions_by_scope.find((s) => s.scope === scope);
    const value = Number(row?.total_co2e ?? 0);
    return { scope, value, count: row?.count ?? 0, share: reportable ? (value / reportable) * 100 : 0 };
  });

  if (a.total === 0) {
    return (
      <div className="space-y-6">
        <PageHeader title="Dashboard" description="Emissions across every connected source." />
        <Card>
          <EmptyState
            icon={Upload}
            title="No activity data yet"
            description="Upload an SAP, utility or travel export to see emissions, review status and anomalies here."
            action={
              <Button asChild>
                <Link to="/app/ingestion">Upload data</Link>
              </Button>
            }
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Reportable emissions exclude flagged and rejected records until they are resolved."
        actions={
          <Button asChild variant="outline">
            <Link to="/app/review">
              Review queue <ArrowRight aria-hidden="true" />
            </Link>
          </Button>
        }
      />

      <section
        aria-label="Key figures"
        className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border bg-border shadow-card lg:grid-cols-5"
      >
        <div className="col-span-2 lg:col-span-1">
          <Kpi
            label="Reportable CO₂e"
            value={formatCO2e(reportable)}
            hint={`${a.total - a.flagged - a.rejected} records`}
          />
        </div>
        <Kpi label="Pending review" value={a.pending_review.toLocaleString()} tone="text-warning" />
        <Kpi
          label="Flagged"
          value={a.flagged.toLocaleString()}
          hint={`${formatCO2e(stats.flagged_co2e)} held back`}
          tone="text-destructive"
        />
        <Kpi label="Approved" value={a.approved.toLocaleString()} tone="text-success" />
        <Kpi label="Locked for audit" value={a.locked.toLocaleString()} tone="text-info" />
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="gap-4 px-5 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-medium text-ink">Monthly emissions by scope</h2>
            <ul className="flex flex-wrap gap-4 text-xs text-muted-foreground" aria-label="Legend">
              {SCOPES.map((s) => (
                <li key={s} className="flex items-center gap-1.5">
                  <span
                    className="size-2 rounded-full"
                    style={{ background: SCOPE_COLORS[s] }}
                    aria-hidden="true"
                  />
                  {scopeLabel(s)}
                </li>
              ))}
            </ul>
          </div>
          <div className="h-72" role="img" aria-label="Stacked bar chart of monthly CO2e by scope">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.emissions_by_month} margin={{ top: 4, right: 4, left: -8, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke={CHART_GRID} />
                <XAxis
                  dataKey="month"
                  tickFormatter={formatMonth}
                  tick={{ fill: CHART_TEXT, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tickFormatter={(v) => formatCO2e(v)}
                  tick={{ fill: CHART_TEXT, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={64}
                />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(20,90,64,0.06)' }} />
                {SCOPES.map((s, i) => (
                  <Bar
                    key={s}
                    dataKey={s}
                    stackId="co2e"
                    fill={SCOPE_COLORS[s]}
                    radius={i === 2 ? [3, 3, 0, 0] : 0}
                    maxBarSize={36}
                    isAnimationActive={false}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="gap-5 px-5">
          <h2 className="font-medium text-ink">Scope breakdown</h2>
          <ul className="space-y-4">
            {byScope.map((s) => (
              <li key={s.scope}>
                <div className="flex items-baseline justify-between gap-2 text-sm">
                  <span className="font-medium text-ink">{scopeLabel(s.scope)}</span>
                  <span className="tabular text-muted-foreground">
                    {formatCO2e(s.value)} · {s.share.toFixed(0)}%
                  </span>
                </div>
                <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-muted" aria-hidden="true">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${Math.max(s.share, 1)}%`, background: SCOPE_COLORS[s.scope] }}
                  />
                </div>
              </li>
            ))}
          </ul>
          <div className="border-t pt-4">
            <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              By category
            </h3>
            <ul className="mt-3 space-y-2.5">
              {stats.emissions_by_category.map((c) => {
                const Icon = CATEGORY_ICONS[c.category] ?? Fuel;
                return (
                  <li key={c.category} className="flex items-center gap-3 text-sm">
                    <span className="flex size-8 items-center justify-center rounded-md bg-secondary text-secondary-foreground">
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    <span className="flex-1">
                      <span className="block font-medium capitalize text-ink">{c.category}</span>
                      <span className="text-xs text-muted-foreground">{c.count} records</span>
                    </span>
                    <span className="tabular font-medium text-ink">{formatCO2e(c.total_co2e)}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        </Card>
      </div>

      <AIBriefing disabled={reportable === 0} />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="gap-0 p-0 lg:col-span-2">
          <div className="flex items-center justify-between px-5 py-4">
            <h2 className="font-medium text-ink">Recent ingestion jobs</h2>
            <Link to="/app/ingestion" className="rounded text-sm font-medium text-primary hover:underline">
              Upload
            </Link>
          </div>
          {stats.recent_jobs.length === 0 ? (
            <EmptyState icon={Upload} title="No uploads yet" />
          ) : (
            <ul className="divide-y border-t">
              {stats.recent_jobs.map((job) => (
                <li key={job.id} className="flex items-center gap-3 px-5 py-3 text-sm">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-ink">{job.original_filename}</p>
                    <p className="text-xs text-muted-foreground">
                      {sourceLabel(job.source_type)} · <span className="tabular">{job.normalized_rows}</span>{' '}
                      normalized · {formatDate(job.created_at)}
                    </p>
                  </div>
                  <StatusBadge status={job.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="gap-3 px-5">
          <h2 className="font-medium text-ink">Data quality</h2>
          <p className="tabular font-display text-4xl font-semibold text-ink">{stats.anomalies.open}</p>
          <p className="text-sm text-muted-foreground">
            open anomalies, {stats.anomalies.resolved + stats.anomalies.ignored} resolved or ignored.
          </p>
          <Button asChild variant="outline" className="mt-auto w-fit">
            <Link to="/app/anomalies">
              Investigate <ArrowRight aria-hidden="true" />
            </Link>
          </Button>
        </Card>
      </div>
    </div>
  );
}
