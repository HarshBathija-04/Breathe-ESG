/**
 * App.tsx - routing. Public: landing + login. Everything under /app needs a session.
 */
import { lazy, Suspense, type ComponentType } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from '@/context/AuthContext';
import { Layout } from '@/components/Layout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { WakeBanner } from '@/components/WakeBanner';
import { Toaster } from '@/components/ui/sonner';
import { LandingPage } from '@/pages/LandingPage';
import { LoginPage } from '@/pages/LoginPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

// Data pages pull in the chart library, so they load on demand.
const DashboardPage = lazy(() => import('@/pages/DashboardPage'));
const IngestionPage = lazy(() => import('@/pages/IngestionPage'));
const ReviewPage = lazy(() => import('@/pages/ReviewPage'));
const AuditPage = lazy(() => import('@/pages/AuditPage'));
const AnomaliesPage = lazy(() => import('@/pages/AnomaliesPage'));

function page(Component: ComponentType) {
  return (
    <Suspense
      fallback={
        <div className="space-y-4" aria-busy="true" aria-label="Loading page">
          <div className="h-8 w-48 animate-pulse rounded-md bg-muted" />
          <div className="h-64 animate-pulse rounded-xl bg-muted" />
        </div>
      }
    >
      <Component />
    </Suspense>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <WakeBanner />
        <Toaster />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={page(DashboardPage)} />
            <Route path="ingestion" element={page(IngestionPage)} />
            <Route path="review" element={page(ReviewPage)} />
            <Route path="anomalies" element={page(AnomaliesPage)} />
            <Route path="audit" element={page(AuditPage)} />
          </Route>
          {/* Old bookmarks from before the /app prefix */}
          {['ingestion', 'review', 'audit', 'anomalies'].map((p) => (
            <Route key={p} path={`/${p}`} element={<Navigate to={`/app/${p}`} replace />} />
          ))}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
