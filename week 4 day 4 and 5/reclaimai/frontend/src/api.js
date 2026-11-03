import axios from "axios";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ||
    "http://127.0.0.1:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const accessToken = localStorage.getItem("token");

    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }

    return config;
  },
  (error) => Promise.reject(error),
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && localStorage.getItem("token")) {
      localStorage.removeItem("token");
      window.dispatchEvent(new Event("reclaimai:unauthorized"));
    }

    return Promise.reject(error);
  },
);

export function apiErrorMessage(error) {
  const body = error?.response?.data?.error;
  if (body?.fields && Object.keys(body.fields).length) {
    return `${body.message} ${Object.entries(body.fields)
      .map(([field, message]) => `${field}: ${message}`)
      .join(" ")}`;
  }
  return body?.message || error?.response?.data?.detail?.message || error?.message || "The request failed.";
}

export function newIdempotencyKey() {
  return crypto.randomUUID();
}

export default api;
