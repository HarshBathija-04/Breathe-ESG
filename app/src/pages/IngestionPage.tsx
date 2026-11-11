/*
Ingestion page - upload SAP, utility and travel exports and inspect each job.
*/
import { useCallback, useEffect, useState, type DragEvent } from 'react';
import { ChevronDown, Database, Download, FileUp, Loader2, Plane, Zap, type LucideIcon } from 'lucide-react';
import { toast } from 'sonner';
import { ingestionApi, type IngestionJob, type SourceKind } from '@/api/ingestion';
import { EmptyState, ErrorState, PageHeader, StatusBadge } from '@/components/common';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDateTime, sourceLabel } from '@/lib/format';
import { messageFromError } from '@/lib/http';
import { cn } from '@/lib/utils';

const SOURCES: Array<{
  kind: SourceKind;
  title: string;
  description: string;
  icon: LucideIcon;
  samples: Array<{ file: string; label: string }>;
}> = [
  {
    kind: 'sap',
    title: 'SAP fuel & procurement',
    description: 'Material movements with plant, quantity and unit. English or German headers.',
    icon: Database,
    samples: [
      { file: 'sap_fuel.csv', label: 'English export' },
      { file: 'sap_fuel_german.csv', label: 'German export' },
    ],
  },
  {
    kind: 'utility',
    title: 'Utility electricity',
    description: 'Meter readings with billing periods in kWh or MWh.',
    icon: Zap,
    samples: [{ file: 'utility_electricity.csv', label: 'Portal export' }],
  },
  {
    kind: 'travel',
    title: 'Corporate travel',
    description: 'Flights, hotels, rail and ground transport from Concur or Navan.',
    icon: Plane,
    samples: [{ file: 'travel_data.csv', label: 'Travel export' }],
  },
];

function UploadZone({
  source,
  busy,
  disabled,
  onUpload,
}: {
  source: (typeof SOURCES)[number];
  busy: boolean;
  disabled: boolean;
  onUpload: (file: File) => void;
}) {
  const [dragging, setDragging] = useState(false);
  const inputId = `upload-${source.kind}`;

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && !disabled) onUpload(file);
  };

  return (
    <Card className="gap-4 px-5">
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
          <source.icon className="size-4" aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-medium text-ink">{source.title}</h2>
          <p className="text-sm text-muted-foreground">{source.description}</p>
        </div>
      </div>

      <label
        htmlFor={inputId}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          'flex min-h-32 cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors duration-150 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2',
          dragging
            ? 'border-primary bg-accent/60'
            : 'border-input hover:border-primary/60 hover:bg-secondary/60',
          disabled && 'cursor-not-allowed opacity-60',
        )}
      >
        {busy ? (
          <Loader2 className="size-5 animate-spin text-primary" aria-hidden="true" />
        ) : (
          <FileUp className="size-5 text-muted-foreground" aria-hidden="true" />
        )}
        <span className="text-sm font-medium text-ink">
          {busy ? 'Processing file' : 'Choose a CSV or drop it here'}
        </span>
        <span className="text-xs text-muted-foreground">Up to 5 MB</span>
        <input
          id={inputId}
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          disabled={disabled}
          aria-label={`Upload ${source.title} CSV`}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onUpload(file);
            e.target.value = '';
          }}
        />
      </label>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
        <span className="text-muted-foreground">Sample data:</span>
        {source.samples.map((s) => (
          <a
            key={s.file}
            href={`/data/${s.file}`}
            download
            className="inline-flex items-center gap-1 rounded font-medium text-primary hover:underline"
          >
            <Download className="size-3" aria-hidden="true" />
            {s.label}
          </a>
        ))}
      </div>
    </Card>
  );
}

function JobRow({ job }: { job: IngestionJob }) {
  const [open, setOpen] = useState(false);
  const pct = job.total_rows ? Math.round((job.normalized_rows / job.total_rows) * 100) : 0;
  return (
    <li>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-5 py-3 text-left text-sm transition-colors duration-150 hover:bg-secondary/60"
      >
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium text-ink">{job.original_filename}</p>
          <p className="text-xs text-muted-foreground">
            {sourceLabel(job.source_type)} · {formatDateTime(job.created_at)} · {job.created_by_name}
          </p>
        </div>
        <div className="hidden w-40 sm:block" aria-hidden="true">
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
          </div>
          <p className="tabular mt-1 text-xs text-muted-foreground">
            {job.normalized_rows}/{job.total_rows} normalized
            {job.flagged_rows > 0 && ` · ${job.flagged_rows} flags`}
          </p>
        </div>
        <StatusBadge status={job.status} />
        <ChevronDown
          className={cn(
            'size-4 shrink-0 text-muted-foreground transition-transform duration-150',
            open && 'rotate-180',
          )}
          aria-hidden="true"
        />
      </button>
      {open && (
        <div className="border-t bg-secondary/40 px-5 py-3">
          <dl className="tabular grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
            {[
              ['Rows', job.total_rows],
              ['Parsed', job.parsed_rows],
              ['Failed', job.failed_rows],
              ['Flagged', job.flagged_rows],
            ].map(([k, v]) => (
              <div key={k as string}>
                <dt className="text-muted-foreground">{k}</dt>
                <dd className="font-medium text-ink">{v}</dd>
              </div>
            ))}
          </dl>
          {job.logs.length > 0 && (
            <ol className="mt-3 max-h-48 space-y-1 overflow-y-auto rounded-md border bg-card p-3 font-mono text-xs">
              {job.logs.map((log, i) => (
                <li
                  key={i}
                  className={
                    log.level === 'ERROR'
                      ? 'text-destructive'
                      : log.level === 'WARN'
                        ? 'text-warning'
                        : 'text-muted-foreground'
                  }
                >
                  <span className="font-semibold">[{log.level}]</span> {log.message}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </li>
  );
}

export default function IngestionPage() {
  const [jobs, setJobs] = useState<IngestionJob[] | null>(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState<SourceKind | null>(null);

  const load = useCallback(async () => {
    setError('');
    try {
      setJobs((await ingestionApi.listJobs()).results);
    } catch (err) {
      setError(messageFromError(err, 'Ingestion history could not be loaded.'));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const upload = async (kind: SourceKind, file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      toast.error('Only .csv files are supported.');
      return;
    }
    setUploading(kind);
    try {
      const job = await ingestionApi.upload(kind, file);
      setJobs((prev) => [job, ...(prev ?? [])]);
      const msg = `${job.normalized_rows} of ${job.total_rows} rows normalized${job.flagged_rows ? `, ${job.flagged_rows} flagged` : ''}.`;
      if (job.status === 'FAILED') toast.error(`${file.name} failed. Open the job to see the log.`);
      else toast.success(`${file.name} ingested`, { description: msg });
    } catch (err) {
      toast.error(messageFromError(err, 'Upload failed. Please try again.'));
    } finally {
      setUploading(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ingestion"
        description="Each file is parsed, normalized into GHG scopes with emission factors, and screened for anomalies."
      />

      <div className="grid gap-4 md:grid-cols-3">
        {SOURCES.map((source) => (
          <UploadZone
            key={source.kind}
            source={source}
            busy={uploading === source.kind}
            disabled={uploading !== null}
            onUpload={(file) => upload(source.kind, file)}
          />
        ))}
      </div>

      <Card className="gap-0 p-0">
        <h2 className="px-5 py-4 font-medium text-ink">Ingestion history</h2>
        {error && !jobs ? (
          <ErrorState message={error} onRetry={load} />
        ) : !jobs ? (
          <div className="space-y-3 border-t p-5" aria-busy="true" aria-label="Loading jobs">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <EmptyState
            icon={FileUp}
            title="No uploads yet"
            description="Start with one of the sample files above."
          />
        ) : (
          <ul className="divide-y border-t">
            {jobs.map((job) => (
              <JobRow key={job.id} job={job} />
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
