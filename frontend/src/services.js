const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
    response = await fetch(`${API_URL}${path}`, options);
  } catch {
    throw new Error('No hay conexión con el backend.');
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

export const jsonRequest = (method, data) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
