const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1";

async function request(path, params = {}) {
  const url = new URL(`${BASE_URL}${path}`);
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null) url.searchParams.set(k, v); });
  const res = await fetch(url.toString());
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.detail || err.message || "Request failed");
  }
  return res.json();
}

export const api = {
  cities:  { list: (sortBy="median_income", order="desc") => request("/cities", { sort_by: sortBy, order }), get: (fips) => request(`/cities/${fips}`) },
  compare: { get: (fipsArray) => request("/compare", { ids: fipsArray.join(",") }) },
  trends:  { get: (fips, months=24) => request(`/trends/${fips}`, { months }) },
  map:     { get: (colorBy="median_income") => request("/map", { color_by: colorBy }) },
  listings:{ get: (fips, listing_type, status, limit=20) => request(`/listings/${fips}`, { listing_type, status, limit }) },
};
