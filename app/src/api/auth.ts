/*
Auth API endpoints.
*/
import apiClient from './client';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthResponse {
  access: string;
  user: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    full_name: string;
    role: string;
    tenant: string;
    tenant_name: string;
  };
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> =>
    (await apiClient.post('/auth/login/', credentials)).data,
  me: async () => (await apiClient.get('/auth/me/')).data,
};
