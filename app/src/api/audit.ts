import apiClient from './client';
import type { Paginated } from './ingestion';

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
  getTimeline: async (params?: {
    entity_type?: string;
    action?: string;
    page?: number;
  }): Promise<Paginated<AuditLogEntry>> => (await apiClient.get('/audit/', { params })).data,
};
