/*
Ingestion API endpoints.
*/
import apiClient from './client';

export type SourceKind = 'sap' | 'utility' | 'travel';

export interface IngestionJob {
  id: string;
  source_system: string;
  source_type: string;
  source_name: string;
  status: string;
  original_filename: string;
  file_size_bytes: number;
  total_rows: number;
  parsed_rows: number;
  failed_rows: number;
  normalized_rows: number;
  flagged_rows: number;
  logs: Array<{ timestamp: string; level: string; message: string; details?: Record<string, unknown> }>;
  created_by: string;
  created_by_name: string;
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const ingestionApi = {
  upload: async (kind: SourceKind, file: File): Promise<IngestionJob> => {
    const formData = new FormData();
    formData.append('file', file);
    return (await apiClient.post(`/ingest/${kind}/`, formData)).data;
  },

  listJobs: async (params?: {
    status?: string;
    source_type?: string;
    page?: number;
  }): Promise<Paginated<IngestionJob>> => (await apiClient.get('/ingest/jobs/', { params })).data,
};
