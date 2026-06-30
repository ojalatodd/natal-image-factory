import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BrainCircuit, Copy, Film, Image as ImageIcon, Plus, Settings, Trash2, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { createProject, deleteProject, duplicateProject, getQueueStatus, listProjects, logout } from "../api";

export default function Dashboard() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const { data: queue = [] } = useQuery({ queryKey: ["queue"], queryFn: getQueueStatus, refetchInterval: 5000 });

  const create = useMutation({
    mutationFn: () => {
      const ts = new Date().toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });
      return createProject(`New Project — ${ts}`);
    },
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      navigate(`/projects/${p.id}`);
    },
  });

  const dup = useMutation({
    mutationFn: (id: number) => duplicateProject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
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
              logout().then(() => navigate("/login"));
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
        <button
          onClick={() => create.mutate()}
          disabled={create.isPending}
          className="flex items-center gap-1 rounded-lg bg-accent px-4 py-2 font-semibold text-white hover:bg-blue-600 disabled:opacity-40"
        >
          {create.isPending ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />} New Project
        </button>
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
                  dup.mutate(p.id);
                }}
                className="text-slate-500 hover:text-white"
                title="Duplicate project"
              >
                <Copy size={16} />
              </button>
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
