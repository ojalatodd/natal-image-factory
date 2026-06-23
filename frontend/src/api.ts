import axios from "axios";

const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export const api = axios.create({ baseURL: BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export interface Project {
  id: number;
  name: string;
  status: string;
  media_mix: string;
  visual_style: string;
  ai_images_enabled: boolean;
  ai_video_motion: boolean;
  audio_duration_s: number | null;
}

export async function login(email: string, password: string) {
  const { data } = await api.post("/auth/login", { email, password });
  localStorage.setItem("token", data.access_token);
  return data;
}

export async function listProjects(): Promise<Project[]> {
  const { data } = await api.get("/projects");
  return data;
}

export async function createProject(name: string): Promise<Project> {
  const { data } = await api.post("/projects", { name });
  return data;
}
