/**
 * App.tsx - Root component with routing
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '@/context/AuthContext';
import { Layout } from '@/components/Layout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { IngestionPage } from '@/pages/IngestionPage';
import { ReviewPage } from '@/pages/ReviewPage';
import { AuditPage } from '@/pages/AuditPage';
import { AnomaliesPage } from '@/pages/AnomaliesPage';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="ingestion" element={<IngestionPage />} />
            <Route path="review" element={<ReviewPage />} />
            <Route path="audit" element={<AuditPage />} />
            <Route path="anomalies" element={<AnomaliesPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
