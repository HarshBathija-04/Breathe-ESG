/*

Dashboard API endpoints.
*/
import apiClient from './client';

export interface DashboardStats {
  activities: {
    total: number;
    pending_review: number;
    flagged: number;
    approved: number;
    locked: number;
    rejected: number;
  };
  emissions_by_scope: Array<{
    scope: string;
    total_co2e: number;
    count: number;
  }>;
  emissions_by_category: Array<{
    category: string;
    total_co2e: number;
    count: number;
  }>;
  recent_jobs: Array<{
    id: string;
    source_type: string;
    status: string;
    original_filename: string;
    total_rows: number;
    parsed_rows: number;
    normalized_rows: number;
    created_at: string;
  }>;
  anomalies: {
    open: number;
    resolved: number;
    confirmed: number;
    ignored: number;
  };
}

export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const response = await apiClient.get('/dashboard/stats/');
    return response.data;
  },
};
