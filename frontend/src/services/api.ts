import axios from "axios";

const getApiBase = () => {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl) {
    const cleanUrl = envUrl.replace(/\/$/, "");
    return cleanUrl.endsWith("/api/v1") ? cleanUrl : `${cleanUrl}/api/v1`;
  }
  return "/api/v1";
};

const api = axios.create({
  baseURL: getApiBase(),
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor to attach token
api.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("token");
        // Redirect to login if not already there
        if (!window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/signup")) {
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

export const API_BASE = getApiBase();
export default api;
