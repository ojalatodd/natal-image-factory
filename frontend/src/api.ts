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
  source_text_key: string | null;
  source_audio_key: string | null;
}

export interface Asset {
  id: number;
  media_type: string;
  source_name: string;
  source_url: string | null;
  license: string | null;
  attribution: string | null;
  thumbnail_url: string | null;
  thumbnail_key: string | null;
  spaces_key: string | null;
  video_key: string | null;
  width: number | null;
  height: number | null;
  duration_s: number | null;
  relevance_score: number | null;
  is_chosen: boolean;
  status: string;
}

export interface Segment {
  id: number;
  index: number;
  start_s: number;
  end_s: number;
  duration_s: number;
  theme_label: string | null;
  summary: string | null;
  chosen_media_type: string | null;
  chosen_asset_id: number | null;
  assets: Asset[];
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

export async function getProject(id: string | number): Promise<Project> {
  const { data } = await api.get(`/projects/${id}`);
  return data;
}

export async function listSegments(projectId: string | number): Promise<Segment[]> {
  const { data } = await api.get(`/projects/${projectId}/segments`);
  return data;
}

export async function swapAsset(segmentId: number, assetId: number): Promise<Segment> {
  const { data } = await api.post(`/segments/${segmentId}/swap`, { asset_id: assetId });
  return data;
}

export async function getDownloadUrl(projectId: string | number): Promise<string> {
  const { data } = await api.get(`/projects/${projectId}/download`);
  return data.url;
}

export async function getVideoUrl(segmentId: number): Promise<string> {
  const { data } = await api.get(`/segments/${segmentId}/video-url`);
  return data.url;
}

export interface SourceConfig {
  id?: number;
  source_name: string;
  media_type: string;
  enabled: boolean;
  priority: number;
}

export async function listSources(): Promise<SourceConfig[]> {
  const { data } = await api.get("/settings/sources");
  return data;
}

export async function updateSources(sources: SourceConfig[]): Promise<SourceConfig[]> {
  const { data } = await api.put("/settings/sources", sources);
  return data;
}

export interface AiSettings {
  id: number;
  provider: string;
  model: string;
  vision_model: string | null;
  image_model: string | null;
}

export async function getAiSettings(): Promise<AiSettings> {
  const { data } = await api.get("/settings/ai");
  return data;
}

export async function updateAiSettings(settings: AiSettings): Promise<AiSettings> {
  const { id, ...payload } = settings;
  const { data } = await api.put("/settings/ai", payload);
  return data;
}

export interface VisualStylePreset {
  value: string;
  label: string;
  summary: string;
  prompt: string;
}

export async function listVisualStyles(): Promise<VisualStylePreset[]> {
  const { data } = await api.get("/visual-styles");
  return data;
}

export async function deleteProject(id: number): Promise<void> {
  await api.delete(`/projects/${id}`);
}

export interface CostEstimate {
  whisper_usd: number;
  segmentation_usd: number;
  ranking_usd: number;
  dalle_fallback_usd: number;
  total_usd: number;
  estimated_segments: number;
  audio_minutes: number;
}

export async function getCostEstimate(projectId: number): Promise<CostEstimate> {
  const { data } = await api.get(`/projects/${projectId}/cost-estimate`);
  return data;
}

export async function getQueueStatus(): Promise<Project[]> {
  const { data } = await api.get("/projects/queue/status");
  return data;
}
