import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BrainCircuit, Film, Image as ImageIcon, Plus, RefreshCw, Settings, Trash2, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createProject, deleteProject, getQueueStatus, listProjects, suggestProjectName } from "../api";

export default function Dashboard() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [nameSuggesting, setNameSuggesting] = useState(false);

  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const { data: queue = [] } = useQuery({ queryKey: ["queue"], queryFn: getQueueStatus, refetchInterval: 5000 });

  async function refreshSuggestedName() {
    setNameSuggesting(true);
    try {
      const suggested = await suggestProjectName();
      setName(suggested);
    } catch {
      // ignore — user can type manually
    } finally {
      setNameSuggesting(false);
    }
  }

  useEffect(() => { refreshSuggestedName(); }, []);

  const create = useMutation({
    mutationFn: () => createProject(name.trim()),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      refreshSuggestedName();
      navigate(`/projects/${p.id}`);
    },
  });

  const del = useMutation({
    mutationFn: (id: number) => deleteProject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });

  return (
    <div className="mx-auto max-w-4xl p-8">
      <header className="mb-8 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ImageIcon className="text-accent" />
          <Film className="text-accent2" />
          <h1 className="text-2xl font-bold text-white">Natal Image Factory</h1>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/settings/sources")}
            className="flex items-center gap-1 text-sm text-slate-400 hover:text-white"
          >
            <Settings size={16} /> Sources
          </button>
          <button
            onClick={() => navigate("/settings/ai")}
            className="flex items-center gap-1 text-sm text-slate-400 hover:text-white"
          >
            <BrainCircuit size={16} /> AI Models
          </button>
          <button
            onClick={() => {
              localStorage.removeItem("token");
              navigate("/login");
            }}
            className="text-sm text-slate-400 hover:text-white"
          >
            Sign out
          </button>
        </div>
      </header>

      {queue.length > 0 && (
        <div className="mb-6 flex items-center gap-2 rounded-lg bg-surface p-3 text-sm text-slate-400">
          <Loader2 size={16} className="animate-spin text-accent" />
          <span>{queue.length} project{queue.length > 1 ? "s" : ""} processing: {queue.map((q) => q.name).join(", ")}</span>
        </div>
      )}

      <div className="mb-8">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              className="w-full rounded-lg bg-surface px-3 py-2 pr-9 text-white outline-none ring-1 ring-card focus:ring-accent"
              placeholder="Project name…"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && create.mutate()}
            />
            <button
              onClick={refreshSuggestedName}
              disabled={nameSuggesting}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white disabled:opacity-40"
              title="Suggest a new name"
            >
              <RefreshCw size={14} className={nameSuggesting ? "animate-spin" : ""} />
            </button>
          </div>
          <button
            onClick={() => create.mutate()}
            disabled={!name.trim()}
            className="flex items-center gap-1 rounded-lg bg-accent px-4 py-2 font-semibold text-white hover:bg-blue-600 disabled:opacity-40"
          >
            <Plus size={18} /> Create
          </button>
        </div>
        <p className="mt-1 text-[11px] text-slate-500">AI-suggested name — edit freely or click ↻ for another.</p>
      </div>

      <div className="grid gap-3">
        {projects.map((p) => (
          <div
            key={p.id}
            className="flex items-center justify-between rounded-lg bg-surface p-4 hover:bg-card"
          >
            <button
              onClick={() => navigate(`/projects/${p.id}`)}
              className="flex-1 text-left"
            >
              <span className="font-medium text-white">{p.name}</span>
            </button>
            <div className="flex items-center gap-3">
              <span className="rounded-full bg-ink px-3 py-1 text-xs uppercase tracking-wide text-slate-400">
                {p.status}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm(`Delete "${p.name}"? This cannot be undone.`)) {
                    del.mutate(p.id);
                  }
                }}
                className="text-slate-500 hover:text-red-400"
                title="Delete project"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}
        {projects.length === 0 && (
          <p className="text-center text-slate-500">No projects yet. Create one to get started.</p>
        )}
      </div>
    </div>
  );
}
