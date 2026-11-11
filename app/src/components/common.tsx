/*
Shared presentational building blocks: brand mark, page header, status and
scope badges, and the empty / error states every data view uses.
*/
import type { ReactNode } from 'react';
import { AlertTriangle, RefreshCw, type LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { humanize, scopeLabel } from '@/lib/format';

export function Logo({ className, inverted = false }: { className?: string; inverted?: boolean }) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <svg viewBox="0 0 64 64" className="size-8 shrink-0" aria-hidden="true">
        <rect
          width="64"
          height="64"
          rx="14"
          className={inverted ? 'fill-primary-foreground' : 'fill-primary'}
        />
        <path
          d="M46 16C30 16 18 24 18 38c0 4 1 7 3 10 2-9 8-17 18-22-8 6-13 13-15 23 3 1 6 2 9 2 13 0 17-14 13-35z"
          className={inverted ? 'fill-primary' : 'fill-primary-foreground'}
        />
      </svg>
      <span
        className={cn(
          'font-display text-lg font-semibold tracking-tight',
          inverted ? 'text-primary-foreground' : 'text-ink',
        )}
      >
        Breathe<span className={inverted ? 'text-primary-foreground/70' : 'text-primary'}>ESG</span>
      </span>
    </span>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-[1.75rem]">
          {title}
        </h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

const STATUS_STYLES: Record<string, string> = {
  PENDING_REVIEW: 'bg-warning-soft text-warning ring-warning/20',
  FLAGGED: 'bg-danger-soft text-destructive ring-destructive/20',
  APPROVED: 'bg-success-soft text-success ring-success/20',
  LOCKED: 'bg-info-soft text-info ring-info/20',
  REJECTED: 'bg-muted text-muted-foreground ring-border',
  OPEN: 'bg-danger-soft text-destructive ring-destructive/20',
  RESOLVED: 'bg-success-soft text-success ring-success/20',
  CONFIRMED: 'bg-warning-soft text-warning ring-warning/20',
  IGNORED: 'bg-muted text-muted-foreground ring-border',
  COMPLETED: 'bg-success-soft text-success ring-success/20',
  PARTIAL: 'bg-warning-soft text-warning ring-warning/20',
  FAILED: 'bg-danger-soft text-destructive ring-destructive/20',
};

const STATUS_LABELS: Record<string, string> = { PENDING_REVIEW: 'Pending', LOCKED: 'Locked' };

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        STATUS_STYLES[status] ?? 'bg-muted text-muted-foreground ring-border',
        className,
      )}
    >
      {STATUS_LABELS[status] ?? humanize(status)}
    </span>
  );
}

const SCOPE_DOT: Record<string, string> = { Scope1: 'bg-scope1', Scope2: 'bg-scope2', Scope3: 'bg-scope3' };

export function ScopeBadge({ scope }: { scope: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-medium text-foreground">
      <span
        className={cn('size-2 rounded-full', SCOPE_DOT[scope] ?? 'bg-muted-foreground')}
        aria-hidden="true"
      />
      {scopeLabel(scope)}
    </span>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-accent text-accent-foreground">
        <Icon className="size-5" aria-hidden="true" />
      </div>
      <p className="font-medium text-ink">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center px-6 py-12 text-center">
      <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-danger-soft text-destructive">
        <AlertTriangle className="size-5" aria-hidden="true" />
      </div>
      <p className="font-medium text-ink">Something went wrong</p>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <Button variant="outline" className="mt-4" onClick={onRetry}>
          <RefreshCw aria-hidden="true" /> Try again
        </Button>
      )}
    </div>
  );
}
