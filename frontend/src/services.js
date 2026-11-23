const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'bf_token';
const USER_KEY = 'bf_user';

export function getUser() {
  try { return JSON.parse(sessionStorage.getItem(USER_KEY) || 'null'); } catch { return null; }
}

export function setSession(data) {
  sessionStorage.setItem(TOKEN_KEY, data.access_token);
  sessionStorage.setItem(USER_KEY, JSON.stringify(data.usuario));
}

export function clearSession() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

function authHeader() {
  const token = sessionStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function errorMessage(body, status) {
  const detail = body?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item?.msg || item?.message).filter(Boolean);
    if (messages.length) return messages.join(' ');
  }
  return `Error ${status}`;
}

export async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers: { ...authHeader(), ...(options.headers || {}) } });
  } catch {
    throw new Error('No hay conexión con el backend.');
  }
  if (response.status === 401 && !path.startsWith('/api/auth/login')) {
    clearSession();
    window.dispatchEvent(new Event('bf-unauthorized'));
  }
  if (!response.ok) {
    let message = `Error ${response.status}`;
    try { message = errorMessage(await response.json(), response.status); } catch { /* response without JSON */ }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  const type = response.headers.get('content-type') || '';
  return type.includes('application/json') ? response.json() : response.blob();
}

export const jsonRequest = (method, data) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data),
});
