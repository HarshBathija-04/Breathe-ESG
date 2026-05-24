/*

Audit API endpoints.
*/
import apiClient from './client';

export interface AuditLogEntry {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  actor: string;
  actor_name: string;
  actor_email: string;
  reason: string;
  timestamp: string;
}

export const auditApi = {
  getTimeline: async (params?: { entity_type?: string; action?: string; page?: number }) => {
    const response = await apiClient.get('/audit/', { params });
    return response.data;
  },

  getEntityHistory: async (entityType: string, entityId: string) => {
    const response = await apiClient.get(`/audit/${entityType}/${entityId}/`);
    return response.data;
  },
};
