import { Link } from 'react-router-dom';
import { Logo } from '@/components/common';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';

export function NotFoundPage() {
  const { isAuthenticated } = useAuth();
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-4 text-center">
      <Logo />
      <p className="tabular mt-10 font-display text-5xl font-semibold text-ink">404</p>
      <h1 className="mt-2 text-lg font-medium text-ink">This page is not in the ledger</h1>
      <p className="mt-1 text-sm text-muted-foreground">The link may be old or mistyped.</p>
      <Button asChild className="mt-6">
        <Link to={isAuthenticated ? '/app' : '/'}>
          {isAuthenticated ? 'Go to dashboard' : 'Back to home'}
        </Link>
      </Button>
    </main>
  );
}
