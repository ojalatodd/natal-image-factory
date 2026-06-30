import { Navigate, Route, Routes } from "react-router-dom";
import { useEffect, useState } from "react";

import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import ProjectView from "./pages/ProjectView";
import AiSettings from "./pages/AiSettings";
import Sources from "./pages/Sources";
import { checkAuth } from "./api";

function RequireAuth({ children }: { children: JSX.Element }) {
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    checkAuth().then(setAuthed);
  }, []);

  if (authed === null) return null; // loading
  return authed ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Dashboard />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/:id"
        element={
          <RequireAuth>
            <ProjectView />
          </RequireAuth>
        }
      />
      <Route
        path="/settings/sources"
        element={
          <RequireAuth>
            <Sources />
          </RequireAuth>
        }
      />
      <Route
        path="/settings/ai"
        element={
          <RequireAuth>
            <AiSettings />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
