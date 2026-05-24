/*

Anomaly API endpoints.
*/
import apiClient from './client';

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

export const anomalyApi = {
  list: async (params?: { status?: string; type?: string; page?: number }) => {
    const response = await apiClient.get('/anomalies/', { params });
    return response.data;
  },

  getStats: async () => {
    const response = await apiClient.get('/anomalies/stats/');
    return response.data;
  },

  resolve: async (flagId: string, status: string, note?: string) => {
    const response = await apiClient.post(`/anomalies/${flagId}/resolve/`, {
      status,
      note,
    });
    return response.data;
  },
};
