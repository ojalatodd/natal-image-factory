import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { listSources, updateSources, type SourceConfig } from "../api";

const DEFAULT_SOURCES: SourceConfig[] = [
  { source_name: "Library of Congress", media_type: "still", enabled: true, priority: 10 },
  { source_name: "Wikimedia Commons", media_type: "still", enabled: true, priority: 20 },
  { source_name: "Internet Archive", media_type: "still", enabled: true, priority: 30 },
  { source_name: "The Met", media_type: "still", enabled: false, priority: 40 },
  { source_name: "Smithsonian Open Access", media_type: "still", enabled: false, priority: 50 },
  { source_name: "Wikimedia Commons Video", media_type: "video", enabled: false, priority: 10 },
  { source_name: "Internet Archive Video", media_type: "video", enabled: false, priority: 20 },
  { source_name: "Pexels", media_type: "video", enabled: false, priority: 30 },
];

export default function Sources() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [sources, setSources] = useState<SourceConfig[]>(DEFAULT_SOURCES);
  const [dirty, setDirty] = useState(false);

  const { data: serverSources } = useQuery({
    queryKey: ["sources"],
    queryFn: listSources,
  });

  useEffect(() => {
    if (serverSources && serverSources.length > 0) {
      setSources(serverSources);
      setDirty(false);
    }
  }, [serverSources]);

  const saveMutation = useMutation({
    mutationFn: (items: SourceConfig[]) => updateSources(items),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sources"] });
      setDirty(false);
    },
  });

  function toggleEnabled(idx: number) {
    setSources((prev) => prev.map((s, i) => (i === idx ? { ...s, enabled: !s.enabled } : s)));
    setDirty(true);
  }

  function movePriority(idx: number, dir: "up" | "down") {
    setSources((prev) => {
      const swapWith = dir === "up" ? idx - 1 : idx + 1;
      if (swapWith < 0 || swapWith >= prev.length) return prev;
      const next = prev.map((s) => ({ ...s }));
      const tmp = next[idx].priority;
      next[idx].priority = next[swapWith].priority;
      next[swapWith].priority = tmp;
      next.sort((a, b) => a.priority - b.priority);
      return next;
    });
    setDirty(true);
  }

  const stills = sources.filter((s) => s.media_type === "still");
  const videos = sources.filter((s) => s.media_type === "video");

  return (
    <div className="mx-auto max-w-3xl p-8">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Source Adapters</h1>
        <button onClick={() => navigate("/")} className="text-sm text-slate-400 hover:text-white">
          Back to dashboard
        </button>
      </header>

      <p className="mb-6 text-sm text-slate-400">
        Enable or disable public-domain media sources and set their priority order. Lower priority number = searched first.
      </p>

      <section className="mb-8">
        <h2 className="mb-3 font-semibold text-white">Still Images</h2>
        <div className="space-y-2">
          {stills.map((s) => {
            const idx = sources.indexOf(s);
            return (
              <div key={`${s.source_name}-${s.media_type}`} className="flex items-center gap-3 rounded-lg bg-surface p-3">
                <label className="flex flex-1 cursor-pointer items-center gap-3">
                  <input type="checkbox" checked={s.enabled} onChange={() => toggleEnabled(idx)} className="h-4 w-4" />
                  <span className={`font-medium ${s.enabled ? "text-white" : "text-slate-500"}`}>{s.source_name}</span>
                </label>
                <span className="text-xs text-slate-400">Priority: {s.priority}</span>
                <button onClick={() => movePriority(idx, "up")} className="rounded p-1 hover:bg-card" title="Move up">
                  <ArrowUp size={16} className="text-slate-400" />
                </button>
                <button onClick={() => movePriority(idx, "down")} className="rounded p-1 hover:bg-card" title="Move down">
                  <ArrowDown size={16} className="text-slate-400" />
                </button>
              </div>
            );
          })}
        </div>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 font-semibold text-white">Video</h2>
        <div className="space-y-2">
          {videos.map((s) => {
            const idx = sources.indexOf(s);
            return (
              <div key={`${s.source_name}-${s.media_type}`} className="flex items-center gap-3 rounded-lg bg-surface p-3">
                <label className="flex flex-1 cursor-pointer items-center gap-3">
                  <input type="checkbox" checked={s.enabled} onChange={() => toggleEnabled(idx)} className="h-4 w-4" />
                  <span className={`font-medium ${s.enabled ? "text-white" : "text-slate-500"}`}>{s.source_name}</span>
                </label>
                <span className="text-xs text-slate-400">Priority: {s.priority}</span>
                <button onClick={() => movePriority(idx, "up")} className="rounded p-1 hover:bg-card" title="Move up">
                  <ArrowUp size={16} className="text-slate-400" />
                </button>
                <button onClick={() => movePriority(idx, "down")} className="rounded p-1 hover:bg-card" title="Move down">
                  <ArrowDown size={16} className="text-slate-400" />
                </button>
              </div>
            );
          })}
        </div>
      </section>

      <button
        onClick={() => saveMutation.mutate(sources)}
        disabled={!dirty || saveMutation.isPending}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent py-3 font-semibold text-white hover:bg-blue-600 disabled:opacity-40"
      >
        <Save size={18} /> {saveMutation.isPending ? "Saving…" : "Save Settings"}
      </button>

      {saveMutation.isSuccess && !dirty && (
        <p className="mt-3 text-center text-sm text-green-400">Settings saved.</p>
      )}
    </div>
  );
}
