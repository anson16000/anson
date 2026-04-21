export async function api(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value === "" || value === null || value === undefined || value === false) return;
    url.searchParams.set(key, value);
  });

  const response = await fetch(url);
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      if (payload?.detail) detail = payload.detail;
      else if (payload?.message) detail = payload.message;
    } catch {
      // ignore non-json error body
    }
    throw new Error(detail);
  }

  const payload = await response.json();
  if (payload.code !== 200) {
    throw new Error(payload.message || "接口返回异常");
  }
  return payload.data;
}
