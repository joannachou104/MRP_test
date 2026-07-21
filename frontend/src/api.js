const BASE = '/api'

function getCurrentUser() {
  try {
    const raw = localStorage.getItem('mrp_current_user')
    if (raw) return JSON.parse(raw)
  } catch (e) {
    // ignore
  }
  return { name: '測試使用者', role: 'admin' }
}

async function request(path, options = {}) {
  const user = getCurrentUser()
  const headers = {
    // Header values must be ISO-8859-1 per the Fetch spec; user.name may contain
    // Chinese characters (e.g. 測試使用者), so percent-encode it for transport.
    'X-User-Name': encodeURIComponent(user.name),
    'X-User-Role': user.role,
    ...(options.headers || {}),
  }
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail || JSON.stringify(data)
    } catch (e) {
      // ignore
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  if (res.status === 204) return null
  const contentType = res.headers.get('content-type') || ''
  if (contentType.includes('application/json')) return res.json()
  return res.text()
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: (path, body) => request(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  patch: (path, body) => request(path, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined }),
  del: (path) => request(path, { method: 'DELETE' }),
  upload: (path, formData) => request(path, { method: 'POST', body: formData }),
}

export { getCurrentUser }
