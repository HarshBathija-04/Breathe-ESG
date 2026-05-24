/*

Ingestion API endpoints.
*/
import apiClient from './client';

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
  logs: Array<{
    timestamp: string;
    level: string;
    message: string;
    details?: Record<string, unknown>;
  }>;
  created_by: string;
  created_by_name: string;
  created_at: string;
}

export const ingestionApi = {
  uploadSAP: async (file: File, sourceSystemId?: string): Promise<IngestionJob> => {
    const formData = new FormData();
    formData.append('file', file);
    if (sourceSystemId) {
      formData.append('source_system_id', sourceSystemId);
    }
    const response = await apiClient.post('/ingest/sap/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  uploadUtility: async (file: File, sourceSystemId?: string): Promise<IngestionJob> => {
    const formData = new FormData();
    formData.append('file', file);
    if (sourceSystemId) {
      formData.append('source_system_id', sourceSystemId);
    }
    const response = await apiClient.post('/ingest/utility/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  uploadTravel: async (file: File, sourceSystemId?: string): Promise<IngestionJob> => {
    const formData = new FormData();
    formData.append('file', file);
    if (sourceSystemId) {
      formData.append('source_system_id', sourceSystemId);
    }
    const response = await apiClient.post('/ingest/travel/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  listJobs: async (params?: { status?: string; source_type?: string }) => {
    const response = await apiClient.get('/ingest/jobs/', { params });
    return response.data;
  },
};
