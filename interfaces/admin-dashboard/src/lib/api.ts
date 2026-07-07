import axios from 'axios';

export const DEFAULT_API_BASE_URL = 'https://helpcentre-dsi-mdr.emergentai.ug';
export const DOCS_URL = 'https://helpcentre-dsi-mdr.emergentai.ug/docs';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL,
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