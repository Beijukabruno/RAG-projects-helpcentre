import axios from 'axios';

export const DEFAULT_API_BASE_URL = 'https://helpcentre-dsi-mdr.emergentai.ug';
export const DOCS_URL = 'http://0.0.0.0:8000/docs';

const DEV_API_BASE_URL = 'http://localhost:8000';
const resolvedBaseUrl =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? DEV_API_BASE_URL : DEFAULT_API_BASE_URL);

export type FeatureFlags = {
  guardrails_enabled: boolean;
  reranker_enabled: boolean;
  chat_history_enabled: boolean;
};

const api = axios.create({
  baseURL: resolvedBaseUrl,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;

export const adminApi = {
  getProjectFeatureFlags: async (projectId: string) => {
    const response = await api.get(`/admin/projects/${projectId}/feature-flags`);
    return response.data as { project_id: string; feature_flags: FeatureFlags & { source?: unknown } };
  },
  updateProjectFeatureFlags: async (projectId: string, flags: Partial<FeatureFlags>) => {
    const response = await api.patch(`/admin/projects/${projectId}/feature-flags`, flags);
    return response.data as { project_id: string; feature_flags: FeatureFlags & { source?: unknown } };
  },
};