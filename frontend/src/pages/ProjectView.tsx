import { useQuery } from "@tanstack/react-query";
import { Download, FileText, Mic, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "../api";

interface ProgressEvent {
  stage: string;
  progress_pct: number;
  message?: string | null;
  error?: string | null;
}

const MEDIA_MIX = [
  { value: "stills", label: "Primarily Stills" },
  { value: "video", label: "Primarily Video" },
  { value: "balanced", label: "Balanced Mix" },
  { value: "ai_judgement", label: "AI Judgement" },
];

const STYLES = ["classical_antiquity", "medieval", "renaissance", "modern", "ai_judgement"];

export default function ProjectView() {
  const { id } = useParams();
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const { data: project, refetch } = useQuery({
    queryKey: ["project", id],
    queryFn: async () => (await api.get(`/projects/${id}`)).data,
  });

  useEffect(() => {
    if (!id) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/api/projects/${id}/progress`);
    ws.onmessage = (e) => {
      const data: ProgressEvent = JSON.parse(e.data);
      setProgress(data);
      if (data.stage === "done" || data.stage === "error") refetch();
    };
    wsRef.current = ws;
    return () => ws.close();
  }, [id, refetch]);

  async function upload(kind: "text" | "audio", file: File) {
    const form = new FormData();
    form.append("file", file);
    await api.post(`/projects/${id}/uploads/${kind}`, form);
    refetch();
  }

  async function updateSetting(patch: Record<string, unknown>) {
    await api.patch(`/projects/${id}/settings`, patch);
    refetch();
  }

  async function generate() {
    await api.post(`/projects/${id}/generate`);
    refetch();
  }

  if (!project) return <div className="p-8 text-slate-400">Loading…</div>;

  return (
    <div className="mx-auto max-w-3xl p-8">
      <h1 className="mb-1 text-2xl font-bold text-white">{project.name}</h1>
      <p className="mb-6 text-sm uppercase tracking-wide text-slate-400">{project.status}</p>

      <section className="mb-6 grid grid-cols-2 gap-3">
        <label className="flex cursor-pointer items-center gap-2 rounded-lg bg-surface p-4 hover:bg-card">
          <FileText className="text-accent" />
          <span>{project.source_text_key ? "Article uploaded" : "Upload article"}</span>
          <input type="file" hidden onChange={(e) => e.target.files && upload("text", e.target.files[0])} />
        </label>
        <label className="flex cursor-pointer items-center gap-2 rounded-lg bg-surface p-4 hover:bg-card">
          <Mic className="text-accent2" />
          <span>{project.source_audio_key ? "Voiceover uploaded" : "Upload voiceover"}</span>
          <input type="file" hidden onChange={(e) => e.target.files && upload("audio", e.target.files[0])} />
        </label>
      </section>

      <section className="mb-6 rounded-lg bg-surface p-4">
        <h2 className="mb-3 font-semibold text-white">Settings</h2>
        <label className="mb-1 block text-sm text-slate-400">Media mix</label>
        <select
          className="mb-4 w-full rounded bg-ink px-3 py-2 text-white"
          value={project.media_mix}
          onChange={(e) => updateSetting({ media_mix: e.target.value })}
        >
          {MEDIA_MIX.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>

        <label className="mb-1 block text-sm text-slate-400">Visual style</label>
        <select
          className="mb-4 w-full rounded bg-ink px-3 py-2 text-white"
          value={project.visual_style}
          onChange={(e) => updateSetting({ visual_style: e.target.value })}
        >
          {STYLES.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </select>

        <label className="mb-2 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={project.ai_images_enabled}
            onChange={(e) => updateSetting({ ai_images_enabled: e.target.checked })}
          />
          Allow AI-generated images as fallback
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={project.ai_video_motion}
            onChange={(e) => updateSetting({ ai_video_motion: e.target.checked })}
          />
          Allow "Motion from Stills" (Ken Burns / animated maps)
        </label>
      </section>

      <button
        onClick={generate}
        disabled={!project.source_audio_key}
        className="mb-6 flex w-full items-center justify-center gap-2 rounded-lg bg-accent py-3 font-semibold text-white hover:bg-blue-600 disabled:opacity-40"
      >
        <Sparkles size={18} /> Generate
      </button>

      {progress && (
        <div className="mb-6 rounded-lg bg-surface p-4">
          <div className="mb-2 flex justify-between text-sm">
            <span className="capitalize text-white">{progress.message || progress.stage}</span>
            <span className="text-slate-400">{progress.progress_pct}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-ink">
            <div
              className="h-2 rounded-full bg-accent transition-all"
              style={{ width: `${progress.progress_pct}%` }}
            />
          </div>
          {progress.error && <p className="mt-2 text-sm text-red-400">{progress.error}</p>}
        </div>
      )}

      {project.status === "complete" && (
        <a
          href={`/api/projects/${id}/download`}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-green-600 py-3 font-semibold text-white hover:bg-green-700"
        >
          <Download size={18} /> Download ZIP
        </a>
      )}
    </div>
  );
}
