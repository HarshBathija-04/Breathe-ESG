/*

Review API endpoints.
*/
import apiClient from './client';

export interface NormalizedActivity {
  id: string;
  tenant: string;
  scope: string;
  category: string;
  sub_category: string;
  activity_value: string;
  normalized_unit: string;
  emission_factor: string;
  emission_factor_source: string;
  co2e: string;
  period_start: string;
  period_end: string;
  status: string;
  edited_flag: boolean;
  edit_reason: string;
  facility_code: string;
  facility_name: string;
  vendor: string;
  notes: string;
  source_record: string;
  source_type: string;
  source_payload: Record<string, unknown>;
  ingestion_job_id: string;
  created_by_name: string;
  created_at: string;
}

export interface ReviewDecision {
  id: string;
  activity: string;
  decision: 'APPROVE' | 'REJECT' | 'REQUEST_INFO';
  reason: string;
  reviewed_by_name: string;
  created_at: string;
}

export const reviewApi = {
  getPending: async (params?: {
    status?: string;
    page?: number;
  }): Promise<{ count: number; results: NormalizedActivity[] }> => {
    const response = await apiClient.get('/review/pending/', { params });
    return response.data;
  },

  submitDecision: async (activityId: string, decision: string, reason?: string) => {
    const response = await apiClient.post(`/review/${activityId}/action/`, {
      decision,
      reason,
    });
    return response.data;
  },

  bulkApprove: async (activityIds: string[], reason?: string) => {
    const response = await apiClient.post('/review/bulk-approve/', {
      activity_ids: activityIds,
      reason,
    });
    return response.data;
  },

  getHistory: async (activityId: string) => {
    const response = await apiClient.get(`/review/${activityId}/history/`);
    return response.data;
  },
};
