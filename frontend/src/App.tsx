import { useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { Menu, X, LogOut, User } from "lucide-react";

import { useCurrentUser, logout, type CurrentUser } from "@/lib/auth";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import MemberDetail from "./pages/MemberDetail";
import OneOnOnePage from "./pages/OneOnOne";
import SimulatorPage from "./pages/Simulator";
import DailyPulsePage from "./pages/DailyPulse";
import ChatPage from "./pages/Chat";
import AdminPage from "./pages/Admin";

import MyDashboard from "./pages/me/MyDashboard";
import MyGoals from "./pages/me/MyGoals";
import MyDaily from "./pages/me/MyDaily";
import MyOneOnOnes from "./pages/me/MyOneOnOnes";

const emNav = [
  { to: "/", label: "ダッシュボード" },
  { to: "/daily-pulse", label: "日報サマリー" },
  { to: "/simulator", label: "組織改編シミュレーション" },
  { to: "/chat", label: "チャット" },
];

const adminNav = [
  ...emNav,
  { to: "/admin", label: "管理" },
];

const memberNav = [
  { to: "/me", label: "ホーム" },
  { to: "/me/goals", label: "目標" },
  { to: "/me/daily", label: "日報" },
  { to: "/me/1on1s", label: "1on1 履歴" },
];

export default function App() {
  const userQ = useCurrentUser();

  if (userQ.isLoading) {
    return <FullPageMessage>読み込み中…</FullPageMessage>;
  }
  if (!userQ.data) {
    return <Login />;
  }

  const user = userQ.data;
  const isAdmin = user.role === "admin";
  const isEmLike = isAdmin || user.role === "em";
  const navItems = isAdmin ? adminNav : isEmLike ? emNav : memberNav;

  return (
    <div className="min-h-screen">
      <Header user={user} navItems={navItems} />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 py-4 sm:py-6">
        {isEmLike ? <EmRoutes isAdmin={isAdmin} /> : <MemberRoutes />}
      </main>
    </div>
  );
}

function EmRoutes({ isAdmin }: { isAdmin: boolean }) {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/members/:id" element={<MemberDetail />} />
      <Route path="/one-on-ones/:memberId" element={<OneOnOnePage />} />
      <Route path="/simulator" element={<SimulatorPage />} />
      <Route path="/daily-pulse" element={<DailyPulsePage />} />
      <Route path="/chat" element={<ChatPage />} />
      {isAdmin && <Route path="/admin" element={<AdminPage />} />}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function MemberRoutes() {
  return (
    <Routes>
      <Route path="/me" element={<MyDashboard />} />
      <Route path="/me/goals" element={<MyGoals />} />
      <Route path="/me/daily" element={<MyDaily />} />
      <Route path="/me/1on1s" element={<MyOneOnOnes />} />
      <Route path="*" element={<Navigate to="/me" replace />} />
    </Routes>
  );
}

function Header({
  user,
  navItems,
}: {
  user: CurrentUser;
  navItems: { to: string; label: string }[];
}) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-30">
      <div className="mx-auto max-w-7xl flex items-center px-4 sm:px-6 py-3">
        <span className="text-xl font-bold text-brand">AtlasLens</span>
        <span className="ml-3 text-xs text-slate-500 hidden sm:inline">
          {user.role === "em" ? "EM-Copilot" : "メンバー"}
        </span>
        <nav className="ml-10 hidden md:flex gap-4">
          {navItems.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/" || n.to === "/me"}
              className={({ isActive }) =>
                `text-sm px-2 py-1 rounded ${
                  isActive ? "text-brand font-semibold" : "text-slate-600 hover:text-slate-900"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          <span className="hidden sm:flex items-center gap-1 text-xs text-slate-500">
            <User size={14} />
            <span className="font-medium text-slate-700">{user.profile?.name ?? user.name}</span>
          </span>
          <button
            onClick={logout}
            className="hidden sm:flex btn-ghost items-center gap-1 text-xs"
            title="ログアウト"
          >
            <LogOut size={14} />
            ログアウト
          </button>
          <button
            className="md:hidden p-2 rounded-md text-slate-600 hover:bg-slate-100"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label="Toggle navigation"
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>
      {menuOpen && (
        <nav className="md:hidden border-t border-slate-200 bg-white">
          {navItems.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/" || n.to === "/me"}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `block px-4 py-3 text-sm border-b border-slate-100 ${
                  isActive
                    ? "text-brand font-semibold bg-brand/5"
                    : "text-slate-700 hover:bg-slate-50"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
          <div className="px-4 py-3 text-xs text-slate-500">
            <p className="mb-2">
              <User size={14} className="inline" />{" "}
              <span className="font-medium text-slate-700">{user.profile?.name ?? user.name}</span>
            </p>
            <button
              onClick={logout}
              className="inline-flex items-center gap-1 text-rose-700"
            >
              <LogOut size={14} />
              ログアウト
            </button>
          </div>
        </nav>
      )}
    </header>
  );
}

function FullPageMessage({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center text-slate-500">
      {children}
    </div>
  );
}
