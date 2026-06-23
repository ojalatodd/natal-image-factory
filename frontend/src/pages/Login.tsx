import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { login } from "../api";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login(email, password);
      navigate("/");
    } catch {
      setError("Invalid credentials");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <form onSubmit={onSubmit} className="w-full max-w-sm rounded-xl bg-surface p-8 shadow-lg">
        <h1 className="mb-1 text-2xl font-bold text-white">Natal Image Factory</h1>
        <p className="mb-6 text-sm text-slate-400">Sign in to continue</p>
        <input
          className="mb-3 w-full rounded-lg bg-ink px-3 py-2 text-white outline-none ring-1 ring-card focus:ring-accent"
          placeholder="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="mb-4 w-full rounded-lg bg-ink px-3 py-2 text-white outline-none ring-1 ring-card focus:ring-accent"
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
        <button className="w-full rounded-lg bg-accent py-2 font-semibold text-white hover:bg-blue-600">
          Sign In
        </button>
      </form>
    </div>
  );
}
