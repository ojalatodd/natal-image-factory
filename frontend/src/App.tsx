import { Navigate, Route, Routes } from "react-router-dom";
import { useEffect, useState } from "react";

import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import ProjectView from "./pages/ProjectView";
import AiSettings from "./pages/AiSettings";
import Sources from "./pages/Sources";
import Admin from "./pages/Admin";
import AccountSettings from "./pages/AccountSettings";
import { checkAuth, getMe, type UserInfo } from "./api";

function RequireAuth({ children, adminOnly }: { children: JSX.Element; adminOnly?: boolean }) {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [user, setUser] = useState<UserInfo | null>(null);

  useEffect(() => {
    checkAuth().then(async (ok) => {
      if (ok) {
        const me = await getMe();
        setUser(me);
        setAuthed(true);
      } else {
        setAuthed(false);
      }
    });
  }, []);

  if (authed === null) return null; // loading
  if (!authed) return <Navigate to="/login" replace />;
  if (adminOnly && user?.role !== "admin") return <Navigate to="/" replace />;
  return children;
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
      <Route
        path="/settings/account"
        element={
          <RequireAuth>
            <AccountSettings />
          </RequireAuth>
        }
      />
      <Route
        path="/admin"
        element={
          <RequireAuth adminOnly>
            <Admin />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
