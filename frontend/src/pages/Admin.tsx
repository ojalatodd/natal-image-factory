import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Trash2, KeyRound, ShieldCheck, User as UserIcon } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { adminCreateUser, adminDeleteUser, adminListUsers, adminResetPassword, adminUpdateRole, type AdminUser } from "../api";

export default function Admin() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: users = [] } = useQuery({ queryKey: ["admin-users"], queryFn: adminListUsers });

  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState<"admin" | "user">("user");

  const createMut = useMutation({
    mutationFn: () => adminCreateUser(newEmail, newPassword, newRole),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      setNewEmail("");
      setNewPassword("");
      setNewRole("user");
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => adminDeleteUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const resetMut = useMutation({
    mutationFn: ({ id, pw }: { id: number; pw: string }) => adminResetPassword(id, pw),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const roleMut = useMutation({
    mutationFn: ({ id, role }: { id: number; role: "admin" | "user" }) => adminUpdateRole(id, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  function handleResetPassword(user: AdminUser) {
    const pw = prompt(`Enter new password for ${user.email}:`);
    if (pw && pw.length >= 4) {
      resetMut.mutate({ id: user.id, pw });
    } else if (pw !== null) {
      alert("Password must be at least 4 characters.");
    }
  }

  return (
    <div className="mx-auto max-w-4xl p-8">
      <button
        onClick={() => navigate("/")}
        className="mb-6 flex items-center gap-1 text-sm text-slate-400 hover:text-white"
      >
        <ArrowLeft size={16} /> Back to Dashboard
      </button>

      <h1 className="mb-6 text-2xl font-bold text-white">Admin Dashboard</h1>

      {/* Add user form */}
      <div className="mb-8 rounded-lg bg-surface p-5">
        <h2 className="mb-4 text-sm font-semibold text-slate-300">Add New User</h2>
        <div className="flex flex-wrap gap-3">
          <input
            type="email"
            placeholder="Email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            className="flex-1 rounded-lg bg-ink px-3 py-2 text-white outline-none ring-1 ring-card focus:ring-accent"
          />
          <input
            type="text"
            placeholder="Password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="flex-1 rounded-lg bg-ink px-3 py-2 text-white outline-none ring-1 ring-card focus:ring-accent"
          />
          <select
            value={newRole}
            onChange={(e) => setNewRole(e.target.value as "admin" | "user")}
            className="rounded-lg bg-ink px-3 py-2 text-white outline-none ring-1 ring-card focus:ring-accent"
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
          <button
            onClick={() => createMut.mutate()}
            disabled={!newEmail || !newPassword}
            className="rounded-lg bg-accent px-4 py-2 font-semibold text-white hover:bg-blue-600 disabled:opacity-40"
          >
            Add User
          </button>
        </div>
        {createMut.isError && (
          <p className="mt-2 text-sm text-red-400">Failed to create user. Email may already be in use.</p>
        )}
      </div>

      {/* Users table */}
      <div className="rounded-lg bg-surface p-5">
        <h2 className="mb-4 text-sm font-semibold text-slate-300">Users ({users.length})</h2>
        <div className="space-y-2">
          {users.map((u) => (
            <div
              key={u.id}
              className="flex items-center justify-between rounded-lg bg-ink px-4 py-3"
            >
              <div className="flex items-center gap-3">
                {u.role === "admin" ? (
                  <ShieldCheck size={18} className="text-accent" />
                ) : (
                  <UserIcon size={18} className="text-slate-500" />
                )}
                <div>
                  <div className="text-sm font-medium text-white">{u.email}</div>
                  <div className="text-xs text-slate-500">
                    {u.role} · {new Date(u.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={u.role}
                  onChange={(e) => roleMut.mutate({ id: u.id, role: e.target.value as "admin" | "user" })}
                  className="rounded bg-card px-2 py-1 text-xs text-white outline-none ring-1 ring-card"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
                <button
                  onClick={() => handleResetPassword(u)}
                  className="text-slate-500 hover:text-white"
                  title="Reset password"
                >
                  <KeyRound size={16} />
                </button>
                <button
                  onClick={() => {
                    if (confirm(`Delete user ${u.email}? This cannot be undone.`)) {
                      deleteMut.mutate(u.id);
                    }
                  }}
                  className="text-slate-500 hover:text-red-400"
                  title="Delete user"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
          {users.length === 0 && (
            <p className="text-center text-slate-500">No users found.</p>
          )}
        </div>
      </div>
    </div>
  );
}
