import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save, SlidersHorizontal } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getAiSettings, updateAiSettings, type AiSettings } from "../api";

const PROVIDERS = [
  {
    id: "openai",
    name: "OpenAI",
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-3.5-turbo"],
    visionModels: ["gpt-4o", "gpt-4.1", "gpt-4o-mini"],
    imageModels: ["dall-e-3", "dall-e-2"],
  },
  {
    id: "anthropic",
    name: "Anthropic",
    models: ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
    visionModels: ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
    imageModels: [],
  },
  {
    id: "gemini",
    name: "Google Gemini",
    models: ["gemini-1.5-pro", "gemini-1.5-flash"],
    visionModels: ["gemini-1.5-pro", "gemini-1.5-flash"],
    imageModels: [],
  },
  {
    id: "deepseek",
    name: "DeepSeek",
    models: ["deepseek-chat", "deepseek-reasoner"],
    visionModels: [],
    imageModels: [],
  },
];

export default function AiSettings() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [draft, setDraft] = useState<AiSettings | null>(null);
  const [dirty, setDirty] = useState(false);

  const { data } = useQuery({
    queryKey: ["ai-settings"],
    queryFn: getAiSettings,
  });

  useEffect(() => {
    if (data) {
      setDraft(data);
      setDirty(false);
    }
  }, [data]);

  const providerConfig = useMemo(() => {
    return PROVIDERS.find((p) => p.id === draft?.provider) ?? PROVIDERS[0];
  }, [draft?.provider]);

  const saveMutation = useMutation({
    mutationFn: (settings: AiSettings) => updateAiSettings(settings),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-settings"] });
      setDirty(false);
    },
  });

  if (!draft) {
    return (
      <div className="mx-auto max-w-3xl p-8 text-slate-300">Loading AI settings…</div>
    );
  }

  const visionModels = providerConfig.visionModels.length
    ? providerConfig.visionModels
    : providerConfig.models;

  const imageModels = providerConfig.imageModels.length
    ? providerConfig.imageModels
    : ["None"];

  return (
    <div className="mx-auto max-w-3xl p-8">
      <header className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="text-accent" size={22} />
          <h1 className="text-2xl font-bold text-white">AI Model Settings</h1>
        </div>
        <button onClick={() => navigate("/")} className="text-sm text-slate-400 hover:text-white">
          Back to dashboard
        </button>
      </header>

      <p className="mb-6 text-sm text-slate-400">
        Select the default AI provider and model used across all projects. If a provider is
        missing an API key or does not support a stage, the pipeline falls back to OpenAI or
        safe placeholder data.
      </p>

      <div className="space-y-6 rounded-xl bg-surface p-6">
        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-200">Provider</label>
          <select
            className="w-full rounded-lg bg-ink px-3 py-2 text-white"
            value={draft.provider}
            onChange={(e) => {
              const nextProvider = e.target.value;
              const nextConfig = PROVIDERS.find((p) => p.id === nextProvider) ?? PROVIDERS[0];
              setDraft((prev) =>
                prev
                  ? {
                      ...prev,
                      provider: nextProvider,
                      model: nextConfig.models[0],
                      vision_model: nextConfig.visionModels[0] ?? nextConfig.models[0],
                      image_model: nextConfig.imageModels[0] ?? null,
                    }
                  : prev
              );
              setDirty(true);
            }}
          >
            {PROVIDERS.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {provider.name}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-200">Text Model</label>
            <select
              className="w-full rounded-lg bg-ink px-3 py-2 text-white"
              value={draft.model}
              onChange={(e) => {
                setDraft({ ...draft, model: e.target.value });
                setDirty(true);
              }}
            >
              {providerConfig.models.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-200">Vision Model</label>
            <select
              className="w-full rounded-lg bg-ink px-3 py-2 text-white"
              value={draft.vision_model ?? ""}
              onChange={(e) => {
                setDraft({ ...draft, vision_model: e.target.value || null });
                setDirty(true);
              }}
            >
              {visionModels.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-200">Image Model</label>
          <select
            className="w-full rounded-lg bg-ink px-3 py-2 text-white"
            value={draft.image_model ?? "None"}
            onChange={(e) => {
              const value = e.target.value === "None" ? null : e.target.value;
              setDraft({ ...draft, image_model: value });
              setDirty(true);
            }}
            disabled={providerConfig.imageModels.length === 0}
          >
            {imageModels.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
          {providerConfig.imageModels.length === 0 && (
            <p className="mt-2 text-xs text-slate-500">
              This provider does not support image generation yet (fallback uses OpenAI if available).
            </p>
          )}
        </div>
      </div>

      <button
        onClick={() => saveMutation.mutate(draft)}
        disabled={!dirty || saveMutation.isPending}
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-accent py-3 font-semibold text-white hover:bg-blue-600 disabled:opacity-40"
      >
        <Save size={18} /> {saveMutation.isPending ? "Saving…" : "Save AI Settings"}
      </button>

      {saveMutation.isSuccess && !dirty && (
        <p className="mt-3 text-center text-sm text-green-400">AI settings saved.</p>
      )}
    </div>
  );
}
