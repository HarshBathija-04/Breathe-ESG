/*
Public landing page: what the product does, how the pipeline works, and a
one-click way into the seeded demo.
*/
import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Bot,
  ClipboardCheck,
  FileSpreadsheet,
  Github,
  Lock,
  ScanSearch,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { warmUpServer } from '@/api/client';
import { Logo } from '@/components/common';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';

const REPO_URL = 'https://github.com/HarshBathija-04/Breathe-ESG';

const features = [
  {
    icon: FileSpreadsheet,
    title: 'Three messy sources, one schema',
    body: 'SAP fuel exports (German headers and decimal commas included), utility portal bills and Concur-style travel files normalize into GHG Protocol scopes.',
  },
  {
    icon: ScanSearch,
    title: 'Anomalies caught before reporting',
    body: 'Negative fuel, consumption spikes, duplicates, missing airports and physically impossible trips are flagged and kept out of totals until resolved.',
  },
  {
    icon: ClipboardCheck,
    title: 'Reviewer sign-off',
    body: 'Role-based approve and reject with reasons. Analysts prepare, reviewers decide, and approved records lock for audit.',
  },
  {
    icon: ShieldCheck,
    title: 'Append-only audit trail',
    body: 'Every ingest, edit, decision and lock is written with before and after snapshots, actor and timestamp.',
  },
  {
    icon: Bot,
    title: 'AI emissions briefing',
    body: 'One click turns the aggregated ledger into an executive summary with hotspots, risks and next steps, powered by Groq.',
  },
  {
    icon: Lock,
    title: 'Raw data never overwritten',
    body: 'Source rows are stored untouched with a SHA-256 hash, so every number traces back to the exact line it came from.',
  },
];

const stages = [
  { label: 'Upload', value: '4 files' },
  { label: 'Parse', value: '183 rows' },
  { label: 'Normalize', value: '174 records' },
  { label: 'Flag', value: '26 anomalies' },
  { label: 'Review', value: '54 approved' },
  { label: 'Lock', value: '27 locked' },
];

function LedgerPreview() {
  const scopes = [
    { name: 'Scope 1', note: 'Fuel', share: 89, className: 'bg-scope1' },
    { name: 'Scope 2', note: 'Electricity', share: 10, className: 'bg-scope2' },
    { name: 'Scope 3', note: 'Travel', share: 1, className: 'bg-scope3' },
  ];
  return (
    <figure
      className="relative rounded-xl border bg-card p-5 shadow-pop sm:p-6"
      aria-label="Example of the emissions ledger"
    >
      <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Reportable emissions
          </p>
          <p className="tabular mt-1 font-display text-3xl font-semibold text-ink">3,279 t CO₂e</p>
        </div>
        <span className="rounded-full bg-danger-soft px-2.5 py-1 text-xs font-medium text-destructive">
          26 flagged held back
        </span>
      </div>
      <div className="mt-5 flex h-2.5 overflow-hidden rounded-full bg-muted" aria-hidden="true">
        {scopes.map((s) => (
          <span key={s.name} className={s.className} style={{ width: `${s.share}%` }} />
        ))}
      </div>
      <ul className="mt-4 grid grid-cols-3 gap-3 text-xs">
        {scopes.map((s) => (
          <li key={s.name}>
            <span className="flex items-center gap-1.5 font-medium text-ink">
              <span className={`size-2 rounded-full ${s.className}`} aria-hidden="true" />
              {s.name}
            </span>
            <span className="text-muted-foreground">
              {s.note} · <span className="tabular">{s.share}%</span>
            </span>
          </li>
        ))}
      </ul>
      <ol className="mt-6 grid grid-cols-3 gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-6">
        {stages.map((stage, i) => (
          <li key={stage.label} className="bg-card px-2.5 py-2">
            <p className="text-[11px] text-muted-foreground">
              <span className="tabular">{String(i + 1).padStart(2, '0')}</span> {stage.label}
            </p>
            <p className="tabular text-xs font-semibold text-ink">{stage.value}</p>
          </li>
        ))}
      </ol>
      <figcaption className="sr-only">
        Seeded demo data: totals by scope and records at each pipeline stage.
      </figcaption>
    </figure>
  );
}

export function LandingPage() {
  const { isAuthenticated } = useAuth();
  useEffect(() => warmUpServer(), []);
  const demoHref = isAuthenticated ? '/app' : '/login';

  return (
    <div className="min-h-dvh bg-background">
      <header className="container flex h-16 items-center justify-between">
        <Logo />
        <nav aria-label="Primary" className="flex items-center gap-1 sm:gap-2">
          <a
            href="#how-it-works"
            className="hidden rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:text-ink sm:inline-block"
          >
            How it works
          </a>
          <Button asChild variant="ghost" size="icon" aria-label="Source code on GitHub">
            <a href={REPO_URL} target="_blank" rel="noreferrer">
              <Github aria-hidden="true" />
            </a>
          </Button>
          <Button asChild>
            <Link to={demoHref}>{isAuthenticated ? 'Open app' : 'Sign in'}</Link>
          </Button>
        </nav>
      </header>

      <main>
        <section className="relative overflow-hidden">
          <div
            className="ledger-grid absolute inset-0 opacity-50 [mask-image:linear-gradient(to_bottom,black,transparent)]"
            aria-hidden="true"
          />
          <div className="container relative grid items-center gap-12 py-14 sm:py-20 lg:grid-cols-[1.05fr_1fr]">
            <div className="animate-fade-up">
              <p className="inline-flex items-center gap-2 rounded-full border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
                <Sparkles className="size-3.5 text-primary" aria-hidden="true" />
                ESG data ingestion, review and audit
              </p>
              <h1 className="mt-5 font-display text-4xl font-semibold leading-[1.08] tracking-tight text-ink sm:text-5xl">
                Emissions data your auditor can trace to the source row.
              </h1>
              <p className="mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
                Breathe ESG turns SAP, utility and travel exports into reviewed, locked GHG Protocol records,
                with anomalies held back from your totals until someone signs them off.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Button asChild size="lg" className="h-11">
                  <Link to={demoHref}>
                    Explore the live demo <ArrowRight aria-hidden="true" />
                  </Link>
                </Button>
                <Button asChild size="lg" variant="outline" className="h-11">
                  <a href="#how-it-works">See the pipeline</a>
                </Button>
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                One-click demo accounts on the sign-in page. No sign-up needed.
              </p>
            </div>
            <LedgerPreview />
          </div>
        </section>

        <section
          id="how-it-works"
          className="border-t bg-card py-16 sm:py-20"
          aria-labelledby="features-title"
        >
          <div className="container">
            <h2
              id="features-title"
              className="max-w-2xl font-display text-3xl font-semibold tracking-tight text-ink"
            >
              Built for the unglamorous part of sustainability reporting
            </h2>
            <p className="mt-3 max-w-2xl text-muted-foreground">
              Every upload goes through the same pipeline: parse, normalize with DEFRA and IEA factors, detect
              anomalies, review, lock. Nothing reaches a report without a human decision on record.
            </p>
            <ul className="mt-10 grid gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-2 lg:grid-cols-3">
              {features.map((f) => (
                <li key={f.title} className="bg-card p-6">
                  <f.icon className="size-5 text-primary" aria-hidden="true" />
                  <h3 className="mt-4 font-medium text-ink">{f.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{f.body}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="py-16 sm:py-20">
          <div className="container flex flex-col items-start justify-between gap-6 rounded-xl border bg-primary px-6 py-10 text-primary-foreground sm:flex-row sm:items-center sm:px-10">
            <div>
              <h2 className="font-display text-2xl font-semibold tracking-tight">
                Try it with real-looking data
              </h2>
              <p className="mt-2 max-w-xl text-sm text-primary-foreground/80">
                The demo tenant ships with four sample exports already ingested, including the broken rows.
              </p>
            </div>
            <Button asChild size="lg" variant="secondary" className="h-11">
              <Link to={demoHref}>
                Open the demo <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
          </div>
        </section>
      </main>

      <footer className="border-t">
        <div className="container flex flex-col gap-2 py-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>Breathe ESG · Django REST + React portfolio project</p>
          <a href={REPO_URL} target="_blank" rel="noreferrer" className="hover:text-ink">
            View source on GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}
