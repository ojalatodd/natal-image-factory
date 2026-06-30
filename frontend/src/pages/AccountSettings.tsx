import { useMutation } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { changePassword, getMe, type UserInfo } from "../api";
import { useQuery } from "@tanstack/react-query";

export default function AccountSettings() {
  const navigate = useNavigate();
  const { data: me } = useQuery<UserInfo>({ queryKey: ["me"], queryFn: getMe });

  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const mut = useMutation({
    mutationFn: () => changePassword(currentPw, newPw),
    onSuccess: () => {
      setSuccess(true);
      setError(null);
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
    },
    onError: () => {
      setError("Failed to change password. Check your current password.");
      setSuccess(false);
    },
  });

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    if (newPw.length < 4) {
      setError("New password must be at least 4 characters.");
      return;
    }
    if (newPw !== confirmPw) {
      setError("New passwords do not match.");
      return;
    }
    mut.mutate();
  }

  return (
    <div className="mx-auto max-w-md p-8">
      <button
        onClick={() => navigate("/")}
        className="mb-6 flex items-center gap-1 text-sm text-slate-400 hover:text-white"
      >
        <ArrowLeft size={16} /> Back to Dashboard
      </button>

      <h1 className="mb-6 text-2xl font-bold text-white">Account Settings</h1>

      {/* Account info */}
      <div className="mb-8 rounded-lg bg-surface p-5">
        <div className="mb-2 text-xs text-slate-500">Email</div>
        <div className="text-sm text-white">{me?.email ?? "…"}</div>
        <div className="mt-3 text-xs text-slate-500">Role</div>
        <div className="text-sm capitalize text-white">{me?.role ?? "…"}</div>
      </div>

      {/* Change password */}
      <form onSubmit={onSubmit} className="rounded-lg bg-surface p-5">
        <h2 className="mb-4 text-sm font-semibold text-slate-300">Change Password</h2>
        <input
          type="password"
          placeholder="Current password"
          value={currentPw}
          onChange={(e) => setCurrentPw(e.target.value)}
          className="mb-3 w-full rounded-lg bg-ink px-3 py-2 text-white outline-none ring-1 ring-card focus:ring-accent"
        />
        <input
          type="password"
          placeholder="New password"
          value={newPw}
          onChange={(e) => setNewPw(e.target.value)}
          className="mb-3 w-full rounded-lg bg-ink px-3 py-2 text-white outline-none ring-1 ring-card focus:ring-accent"
        />
        <input
          type="password"
          placeholder="Confirm new password"
          value={confirmPw}
          onChange={(e) => setConfirmPw(e.target.value)}
          className="mb-4 w-full rounded-lg bg-ink px-3 py-2 text-white outline-none ring-1 ring-card focus:ring-accent"
        />
        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
        {success && <p className="mb-3 text-sm text-green-400">Password changed successfully.</p>}
        <button
          type="submit"
          disabled={!currentPw || !newPw || !confirmPw}
          className="w-full rounded-lg bg-accent py-2 font-semibold text-white hover:bg-blue-600 disabled:opacity-40"
        >
          Change Password
        </button>
      </form>
    </div>
  );
}
