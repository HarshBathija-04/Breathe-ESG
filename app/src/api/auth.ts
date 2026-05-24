/*

Auth API endpoints.
*/
import apiClient from './client';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  tenant: string;
  role: string;
}

export interface AuthResponse {
  access: string;
  user: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    role: string;
    tenant: string;
    tenant_name: string;
  };
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const response = await apiClient.post('/auth/login/', credentials);
    return response.data;
  },

  register: async (data: RegisterData): Promise<AuthResponse> => {
    const response = await apiClient.post('/auth/register/', data);
    return response.data;
  },

  me: async () => {
    const response = await apiClient.get('/auth/me/');
    return response.data;
  },
};
