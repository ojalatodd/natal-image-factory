import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle, Download, FileText, Mic, RefreshCw, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api, deleteProject, getCostEstimate, getDownloadUrl, listSegments, listVisualStyles, swapAsset, type CostEstimate, type Segment, type VisualStylePreset } from "../api";

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

const DEFAULT_STYLE = "ai_judgement";

function formatTimestamp(s: number): string {
  const total = Math.floor(s);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const sec = total % 60;
  if (h > 0) return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

export default function ProjectView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [costEst, setCostEst] = useState<CostEstimate | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const qc = useQueryClient();

  const { data: project, refetch } = useQuery({
    queryKey: ["project", id],
    queryFn: async () => (await api.get(`/projects/${id}`)).data,
  });

  const { data: styles = [] } = useQuery({
    queryKey: ["visual-styles"],
    queryFn: listVisualStyles,
  });

  const { data: segments = [], refetch: refetchSegs } = useQuery({
    queryKey: ["segments", id],
    queryFn: () => listSegments(id!),
    enabled: !!id && (project?.status === "review" || project?.status === "complete"),
  });

  useEffect(() => {
    if (!id) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/api/projects/${id}/progress`);
    ws.onmessage = (e) => {
      const data: ProgressEvent = JSON.parse(e.data);
      setProgress(data);
      if (data.stage === "done" || data.stage === "error") {
        refetch();
        refetchSegs();
      }
    };
    wsRef.current = ws;
    return () => ws.close();
  }, [id, refetch, refetchSegs]);

  useEffect(() => {
    if (project && (project.status === "review" || project.status === "complete")) {
      getDownloadUrl(id!).then(setDownloadUrl).catch(() => setDownloadUrl(null));
    }
  }, [project, id]);

  const swapMutation = useMutation({
    mutationFn: ({ segId, assetId }: { segId: number; assetId: number }) => swapAsset(segId, assetId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["segments", id] }),
  });

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
    setProgress(null);
    setDownloadUrl(null);
    setCostEst(null);
    await api.post(`/projects/${id}/generate`);
    refetch();
  }

  async function fetchCostEstimate() {
    try {
      const est = await getCostEstimate(Number(id));
      setCostEst(est);
    } catch {
      setCostEst(null);
    }
  }

  if (!project) return <div className="p-8 text-slate-400">Loading…</div>;

  const canGenerate = project.source_audio_key && project.source_text_key;
  const showSegments = project.status === "review" || project.status === "complete";

  return (
    <div className="mx-auto max-w-4xl p-8">
      <div className="mb-1 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">{project.name}</h1>
        {project.status !== "processing" && (
          <button
            onClick={() => {
              if (confirm(`Delete "${project.name}"? This cannot be undone.`)) {
                deleteProject(Number(id)).then(() => navigate("/"));
              }
            }}
            className="flex items-center gap-1 text-sm text-slate-500 hover:text-red-400"
          >
            <Trash2 size={16} /> Delete
          </button>
        )}
      </div>
      <p className="mb-6 text-sm uppercase tracking-wide text-slate-400">{project.status}</p>

      {/* Upload section */}
      <section className="mb-6 grid grid-cols-2 gap-3">
        <label className="flex cursor-pointer items-center gap-2 rounded-lg bg-surface p-4 hover:bg-card">
          <FileText className="text-accent" />
          <span>{project.source_text_key ? "Article uploaded ✓" : "Upload article text"}</span>
          <input type="file" hidden accept=".txt,.md,.text" onChange={(e) => e.target.files && upload("text", e.target.files[0])} />
        </label>
        <label className="flex cursor-pointer items-center gap-2 rounded-lg bg-surface p-4 hover:bg-card">
          <Mic className="text-accent2" />
          <span>{project.source_audio_key ? "Voiceover uploaded ✓" : "Upload voiceover"}</span>
          <input type="file" hidden accept="audio/*" onChange={(e) => e.target.files && upload("audio", e.target.files[0])} />
        </label>
      </section>

      {/* Settings */}
      <section className="mb-6 rounded-lg bg-surface p-4">
        <h2 className="mb-3 font-semibold text-white">Settings</h2>
        <label className="mb-1 block text-sm text-slate-400">Media mix</label>
        <select
          className="mb-4 w-full rounded bg-ink px-3 py-2 text-white"
          value={project.media_mix}
          onChange={(e) => updateSetting({ media_mix: e.target.value })}
        >
          {MEDIA_MIX.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>

        <label className="mb-2 block text-sm text-slate-400">Visual style presets</label>
        <div className="mb-4 grid grid-cols-1 gap-2 md:grid-cols-2">
          {(styles.length
            ? styles
            : ([{ value: DEFAULT_STYLE, label: "AI Selects Best", summary: "Let the pipeline decide", prompt: "" }] satisfies VisualStylePreset[]))
            .map((style) => {
            const isSelected = project.visual_style === style.value;
            return (
              <button
                key={style.value}
                type="button"
                onClick={() => updateSetting({ visual_style: style.value })}
                className={`rounded-lg border px-3 py-2 text-left transition ${isSelected ? "border-accent bg-accent/10" : "border-slate-700 hover:border-accent/50"}`}
              >
                <p className="text-sm font-semibold text-white">{style.label}</p>
                <p className="text-xs text-slate-400">{style.summary}</p>
                {style.prompt && <p className="mt-1 text-[11px] text-slate-500">Prompt hint: {style.prompt}</p>}
              </button>
            );
          })}
        </div>

        <label className="mb-2 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={project.ai_images_enabled} onChange={(e) => updateSetting({ ai_images_enabled: e.target.checked })} />
          Allow AI-generated images as fallback
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={project.ai_video_motion} onChange={(e) => updateSetting({ ai_video_motion: e.target.checked })} />
          Allow "Motion from Stills" (Ken Burns / animated maps)
        </label>
      </section>

      {/* Generate button + cost estimate */}
      <button
        onClick={generate}
        disabled={!canGenerate || project.status === "processing"}
        className="mb-2 flex w-full items-center justify-center gap-2 rounded-lg bg-accent py-3 font-semibold text-white hover:bg-blue-600 disabled:opacity-40"
      >
        {project.status === "processing" ? <RefreshCw size={18} className="animate-spin" /> : <Sparkles size={18} />}
        {project.status === "processing" ? "Processing…" : showSegments ? "Regenerate" : "Generate"}
      </button>

      {canGenerate && project.status !== "processing" && (
        <div className="mb-6">
          <button
            onClick={fetchCostEstimate}
            className="text-xs text-slate-400 hover:text-white"
          >
            {costEst ? "Refresh cost estimate" : "Estimate API cost →"}
          </button>
          {costEst && (
            <div className="mt-2 rounded-lg bg-surface p-3 text-xs text-slate-400">
              <div className="mb-1 flex justify-between">
                <span>Whisper transcription</span>
                <span>${costEst.whisper_usd.toFixed(4)}</span>
              </div>
              <div className="mb-1 flex justify-between">
                <span>Segmentation (GPT-4o-mini)</span>
                <span>${costEst.segmentation_usd.toFixed(4)}</span>
              </div>
              <div className="mb-1 flex justify-between">
                <span>Vision ranking ({costEst.estimated_segments} segments)</span>
                <span>${costEst.ranking_usd.toFixed(4)}</span>
              </div>
              {costEst.dalle_fallback_usd > 0 && (
                <div className="mb-1 flex justify-between">
                  <span>DALL-E fallback (if needed)</span>
                  <span>${costEst.dalle_fallback_usd.toFixed(4)}</span>
                </div>
              )}
              <div className="mt-2 flex justify-between border-t border-slate-700 pt-2 font-semibold text-white">
                <span>Estimated total</span>
                <span>${costEst.total_usd.toFixed(4)}</span>
              </div>
              <p className="mt-1 text-[11px] text-slate-500">Based on {costEst.audio_minutes} min of audio. Actual usage may vary.</p>
            </div>
          )}
        </div>
      )}

      {/* Progress bar */}
      {progress && (
        <div className="mb-6 rounded-lg bg-surface p-4">
          <div className="mb-2 flex justify-between text-sm">
            <span className="capitalize text-white">{progress.message || progress.stage}</span>
            <span className="text-slate-400">{progress.progress_pct}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-ink">
            <div className="h-2 rounded-full bg-accent transition-all" style={{ width: `${progress.progress_pct}%` }} />
          </div>
          {progress.error && <p className="mt-2 text-sm text-red-400">{progress.error}</p>}
        </div>
      )}

      {/* Segment review */}
      {showSegments && segments.length > 0 && (
        <section className="mb-6">
          <h2 className="mb-3 font-semibold text-white">Segments ({segments.length})</h2>
          <div className="space-y-3">
            {segments.map((seg: Segment) => (
              <div key={seg.id} className="rounded-lg bg-surface p-4">
                <div className="mb-2 flex items-center justify-between">
                  <div>
                    <span className="text-xs text-slate-400">#{seg.index}</span>
                    <span className="ml-2 font-medium text-white">{seg.theme_label || `Segment ${seg.index}`}</span>
                  </div>
                  <span className="text-xs text-slate-400">
                    {formatTimestamp(seg.start_s)} – {formatTimestamp(seg.end_s)}
                  </span>
                </div>
                {seg.summary && <p className="mb-3 text-sm text-slate-400">{seg.summary}</p>}

                {/* Chosen asset preview */}
                {seg.chosen_asset_id && (
                  <div className="mb-2">
                    <p className="mb-1 text-xs text-green-400">✓ Chosen: {seg.assets.find(a => a.id === seg.chosen_asset_id)?.source_name}</p>
                  </div>
                )}

                {/* Asset thumbnails */}
                {seg.assets.length > 0 && (
                  <div className="flex gap-2 overflow-x-auto pb-2">
                    {seg.assets.map((asset) => (
                      <button
                        key={asset.id}
                        onClick={() => swapMutation.mutate({ segId: seg.id, assetId: asset.id })}
                        className={`relative flex-shrink-0 overflow-hidden rounded-lg border-2 transition-all ${
                          asset.is_chosen ? "border-accent" : "border-transparent hover:border-card"
                        }`}
                        title={asset.attribution || asset.source_name}
                      >
                        {asset.thumbnail_url && (
                          <img src={asset.thumbnail_url} alt={asset.source_name} className="h-20 w-20 object-cover" />
                        )}
                        {!asset.thumbnail_url && (
                          <div className="flex h-20 w-20 items-center justify-center bg-ink text-xs text-slate-500">No preview</div>
                        )}
                        {asset.is_chosen && (
                          <div className="absolute bottom-0 right-0 rounded-tl bg-accent p-0.5">
                            <CheckCircle size={14} className="text-white" />
                          </div>
                        )}
                        <div className="absolute bottom-0 left-0 right-0 bg-black/60 px-1 py-0.5 text-[10px] text-slate-300">
                          {asset.source_name}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
                {seg.assets.length === 0 && (
                  <p className="text-xs text-slate-500">No candidates found for this segment.</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Download */}
      {showSegments && downloadUrl && (
        <a
          href={downloadUrl}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-green-600 py-3 font-semibold text-white hover:bg-green-700"
        >
          <Download size={18} /> Download ZIP
        </a>
      )}
    </div>
  );
}
