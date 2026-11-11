import apiClient from './client';

export type ScopeKey = 'Scope1' | 'Scope2' | 'Scope3';

export interface RecentJob {
  id: string;
  source_type: string;
  status: string;
  original_filename: string;
  total_rows: number;
  parsed_rows: number;
  normalized_rows: number;
  created_at: string;
}

export interface DashboardStats {
  activities: {
    total: number;
    pending_review: number;
    flagged: number;
    approved: number;
    locked: number;
    rejected: number;
  };
  emissions_by_scope: Array<{ scope: ScopeKey; total_co2e: number; count: number }>;
  emissions_by_category: Array<{ category: string; total_co2e: number; count: number }>;
  emissions_by_month: Array<{ month: string } & Partial<Record<ScopeKey, number>>>;
  flagged_co2e: number;
  recent_jobs: RecentJob[];
  anomalies: { open: number; resolved: number; confirmed: number; ignored: number };
}

export interface Briefing {
  headline: string;
  summary: string;
  highlights: string[];
  risks: string[];
  recommendations: string[];
  model: string;
  context: { total_kg_co2e: number; record_count: number };
}

export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => (await apiClient.get('/dashboard/stats/')).data,
  generateBriefing: async (): Promise<Briefing> => (await apiClient.post('/dashboard/insights/')).data,
};
