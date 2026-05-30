import { useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { Menu, X, LogOut, User, Compass } from "lucide-react";

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

interface NavItem {
  to: string;
  label: string;
  hint?: string;
}

const emNav: NavItem[] = [
  { to: "/", label: "ダッシュボード", hint: "チーム全員の状況" },
  { to: "/daily-pulse", label: "日報サマリー", hint: "AI 要約 + 履歴" },
  { to: "/simulator", label: "組織改編シミュレーション", hint: "Plan→Critique→Refine" },
  { to: "/chat", label: "チャット", hint: "ツールを呼ぶ Agent" },
];

const adminNav: NavItem[] = [...emNav, { to: "/admin", label: "管理", hint: "アカウント / 組織" }];

const memberNav: NavItem[] = [
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
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Header user={user} navItems={navItems} />
      <main className="mx-auto w-full max-w-7xl px-4 sm:px-6 py-6 sm:py-8 flex-1">
        {isEmLike ? <EmRoutes isAdmin={isAdmin} /> : <MemberRoutes />}
      </main>
      <Footer />
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
  navItems: NavItem[];
}) {
  const [menuOpen, setMenuOpen] = useState(false);

  const roleBadge =
    user.role === "admin" ? "Admin" : user.role === "em" ? "EM-Copilot" : "メンバー";

  return (
    <header className="border-b border-slate-200 bg-white/95 backdrop-blur sticky top-0 z-30">
      <div className="mx-auto max-w-7xl flex items-center px-4 sm:px-6 py-3 gap-4">
        <NavLink to="/" className="flex items-center gap-2 shrink-0">
          <span className="grid place-items-center w-7 h-7 rounded-lg bg-brand text-white">
            <Compass size={16} />
          </span>
          <span className="text-lg font-bold text-slate-900 tracking-tight">AtlasLens</span>
          <span className="hidden sm:inline pill-brand text-[10px] uppercase">{roleBadge}</span>
        </NavLink>

        <nav className="ml-4 hidden md:flex gap-1 flex-1">
          {navItems.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/" || n.to === "/me"}
              title={n.hint}
              className={({ isActive }) =>
                `text-sm px-3 py-1.5 rounded-md transition ${
                  isActive
                    ? "bg-brand/10 text-brand-dark font-semibold"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          <span className="hidden sm:flex items-center gap-1.5 text-xs text-slate-500">
            <User size={14} className="text-slate-400" />
            <span className="font-medium text-slate-700">
              {user.profile?.name ?? user.name}
            </span>
          </span>
          <button
            onClick={logout}
            className="hidden sm:inline-flex btn-ghost btn-xs items-center gap-1"
            title="ログアウト"
          >
            <LogOut size={12} />
            ログアウト
          </button>
          <button
            className="md:hidden p-2 rounded-md text-slate-600 hover:bg-slate-100"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label="メニューを開閉"
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {menuOpen && (
        <nav className="md:hidden border-t border-slate-200 bg-white animate-fade-in">
          {navItems.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/" || n.to === "/me"}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `block px-4 py-3 text-sm border-b border-slate-100 ${
                  isActive
                    ? "text-brand-dark font-semibold bg-brand/5"
                    : "text-slate-700 hover:bg-slate-50"
                }`
              }
            >
              <div>{n.label}</div>
              {n.hint && <div className="text-[11px] text-slate-400 mt-0.5">{n.hint}</div>}
            </NavLink>
          ))}
          <div className="px-4 py-3 text-xs text-slate-500 flex items-center justify-between">
            <span className="inline-flex items-center gap-1">
              <User size={14} className="text-slate-400" />
              <span className="font-medium text-slate-700">
                {user.profile?.name ?? user.name}
              </span>
            </span>
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

function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 py-3 text-xs text-slate-400 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
        <span>AtlasLens — EM Co-pilot powered by Azure AI Foundry</span>
        <span>
          観察対象は行動データのみ。感情・メンタル状態は推測しません。
        </span>
      </div>
    </footer>
  );
}

function FullPageMessage({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center text-slate-500">
      {children}
    </div>
  );
}
