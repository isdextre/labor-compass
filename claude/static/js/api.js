/* ============================================================================
   api.js — Helper de comunicación con el backend Flask
   ============================================================================
   Al servir las páginas desde el propio Flask (Jinja), el frontend y la API
   viven en el mismo origen: no hace falta CORS ni una URL base absoluta,
   rutas relativas alcanzan.
   ========================================================================= */

async function apiFetch(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const isJson = res.headers.get('content-type')?.includes('application/json');
  const body = isJson ? await res.json().catch(() => ({})) : null;
  if (!res.ok) {
    throw new Error(body?.error || `Error ${res.status} en ${path}`);
  }
  return body;
}

function apiPost(path, data) {
  return apiFetch(path, { method: 'POST', body: JSON.stringify(data) });
}

function apiGet(path) {
  return apiFetch(path);
}
