/** Formatting helpers shared by every page (kept pure so they are unit-tested). */

/** kg CO2e -> human string, switching to tonnes from 1,000 kg. */
export function formatCO2e(kg: number | string | null | undefined): string {
  const value = Number(kg ?? 0);
  if (!Number.isFinite(value)) return '-';
  const abs = Math.abs(value);
  if (abs >= 1_000_000)
    return `${(value / 1_000_000).toLocaleString('en-US', { maximumFractionDigits: 2 })} kt`;
  if (abs >= 1_000) return `${(value / 1_000).toLocaleString('en-US', { maximumFractionDigits: 1 })} t`;
  return `${value.toLocaleString('en-US', { maximumFractionDigits: 1 })} kg`;
}

export function formatNumber(value: number | string | null | undefined, digits = 2): string {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? n.toLocaleString('en-US', { maximumFractionDigits: digits }) : '-';
}

export function formatDate(iso: string | null | undefined, opts?: Intl.DateTimeFormatOptions): string {
  if (!iso) return '-';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '-';
  return d.toLocaleDateString('en-US', opts ?? { day: 'numeric', month: 'short', year: 'numeric' });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '-';
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? '-'
    : d.toLocaleString('en-US', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

/** "2024-03" -> "Mar 24" */
export function formatMonth(key: string): string {
  const [y, m] = key.split('-').map(Number);
  if (!y || !m) return key;
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString('en-US', {
    month: 'short',
    year: '2-digit',
    timeZone: 'UTC',
  });
}

/** SNAKE_CASE / snake_case -> "Snake case" */
export function humanize(value: string | null | undefined): string {
  if (!value) return '';
  const text = value.replace(/_/g, ' ').toLowerCase();
  const sentence = text.charAt(0).toUpperCase() + text.slice(1);
  // Fuel acronyms stay uppercase ("LPG", not "Lpg").
  return sentence.replace(/\b(lpg|lng|cng|hvo)\b/gi, (m) => m.toUpperCase());
}

export function scopeLabel(scope: string): string {
  return scope.replace(/^Scope(\d)$/, 'Scope $1');
}

const SOURCE_LABELS: Record<string, string> = {
  SAP: 'SAP',
  UTILITY: 'Utility',
  TRAVEL: 'Travel',
  MANUAL: 'Manual',
};

export function sourceLabel(sourceType: string): string {
  return SOURCE_LABELS[sourceType] ?? humanize(sourceType);
}
