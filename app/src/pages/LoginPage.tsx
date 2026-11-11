/*
Login page - email/password sign-in plus one-click demo accounts.
*/
import { useEffect, useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { AlertCircle, ArrowRight, Loader2 } from 'lucide-react';
import { warmUpServer } from '@/api/client';
import { Logo } from '@/components/common';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/context/AuthContext';
import { messageFromError } from '@/lib/http';

const DEMO_ACCOUNTS = [
  {
    email: 'reviewer@democorp.com',
    password: 'reviewer123',
    role: 'Reviewer',
    note: 'Approve, reject and lock records',
  },
  {
    email: 'analyst@democorp.com',
    password: 'analyst123',
    role: 'Analyst',
    note: 'Upload files and prepare data',
  },
  { email: 'admin@democorp.com', password: 'admin123', role: 'Admin', note: 'Everything, plus Django admin' },
];

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const { login, isAuthenticated } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(
    params.get('expired') ? 'Your session expired. Please sign in again.' : '',
  );
  const [submitting, setSubmitting] = useState<string | null>(null);

  useEffect(() => warmUpServer(), []);

  const from = (location.state as { from?: string } | null)?.from ?? '/app';
  if (isAuthenticated) return <Navigate to={from} replace />;

  const signIn = async (address: string, secret: string, key: string) => {
    setError('');
    setSubmitting(key);
    try {
      await login(address, secret);
      navigate(from, { replace: true });
    } catch (err) {
      setError(messageFromError(err, 'Sign in failed. Please try again.'));
      setSubmitting(null);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    signIn(email, password, 'form');
  };

  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <aside className="relative hidden overflow-hidden bg-primary p-12 text-primary-foreground lg:flex lg:flex-col lg:justify-between">
        <div className="ledger-grid absolute inset-0 opacity-[0.07]" aria-hidden="true" />
        <Link to="/" className="relative w-fit rounded-md" aria-label="Breathe ESG home">
          <Logo inverted />
        </Link>
        <blockquote className="relative max-w-md">
          <p className="font-display text-3xl font-medium leading-snug">
            “If it is not on the audit trail, it did not happen.”
          </p>
          <footer className="mt-4 text-sm text-primary-foreground/75">
            Every upload, edit, approval and lock in Breathe ESG is recorded with who, when and why.
          </footer>
        </blockquote>
        <p className="relative text-xs text-primary-foreground/70">Demo tenant: Northwind Manufacturing</p>
      </aside>

      <main className="flex items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-sm">
          <Link to="/" className="mb-10 inline-block rounded-md lg:hidden">
            <Logo />
          </Link>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">Sign in</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Use a demo account below or your own credentials.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4" noValidate={false}>
            {error && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-lg bg-danger-soft p-3 text-sm text-destructive"
              >
                <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                {error}
              </div>
            )}
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="h-10"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="h-10"
              />
            </div>
            <Button type="submit" className="h-10 w-full" disabled={!!submitting}>
              {submitting === 'form' ? <Loader2 className="animate-spin" aria-hidden="true" /> : null}
              {submitting === 'form' ? 'Signing in' : 'Sign in'}
            </Button>
          </form>

          <div className="mt-10">
            <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              One-click demo accounts
            </h2>
            <ul className="mt-3 divide-y overflow-hidden rounded-lg border bg-card">
              {DEMO_ACCOUNTS.map((account) => (
                <li key={account.email}>
                  <button
                    type="button"
                    disabled={!!submitting}
                    onClick={() => signIn(account.email, account.password, account.email)}
                    className="group flex w-full items-center gap-3 px-4 py-3 text-left transition-colors duration-150 hover:bg-secondary disabled:opacity-60"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-ink">{account.role}</span>
                      <span className="block truncate text-xs text-muted-foreground">{account.note}</span>
                    </span>
                    {submitting === account.email ? (
                      <Loader2 className="size-4 animate-spin text-primary" aria-label="Signing in" />
                    ) : (
                      <ArrowRight
                        className="size-4 text-muted-foreground transition-transform duration-150 group-hover:translate-x-0.5"
                        aria-hidden="true"
                      />
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </main>
    </div>
  );
}
