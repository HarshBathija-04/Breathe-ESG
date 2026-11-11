import apiClient from './client';
import type { Paginated } from './ingestion';

export interface AnomalyFlag {
  id: string;
  activity: string;
  activity_details: {
    id: string;
    category: string;
    sub_category: string;
    scope: string;
    co2e: string;
    status: string;
    period_start: string;
    period_end: string;
  };
  anomaly_type: string;
  description: string;
  confidence: string;
  details: Record<string, unknown>;
  status: string;
  resolved_by_name: string;
  resolution_note: string;
  resolved_at: string;
  created_at: string;
}

export interface AnomalyStats {
  by_status: Array<{ status: string; count: number }>;
  by_type: Array<{ anomaly_type: string; count: number }>;
}

export const anomalyApi = {
  list: async (params?: { status?: string; type?: string; page?: number }): Promise<Paginated<AnomalyFlag>> =>
    (await apiClient.get('/anomalies/', { params })).data,
  getStats: async (): Promise<AnomalyStats> => (await apiClient.get('/anomalies/stats/')).data,
  resolve: async (flagId: string, status: string, note?: string) =>
    (await apiClient.post(`/anomalies/${flagId}/resolve/`, { status, note })).data,
};
