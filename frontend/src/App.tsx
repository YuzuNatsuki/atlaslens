import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import {
  CalendarDays,
  Compass,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  Settings2,
  Sparkles,
  Target,
  User,
  X,
} from "lucide-react";

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

import type { LucideIcon } from "lucide-react";

interface NavItem {
  to: string;
  label: string;
  hint?: string;
  icon: LucideIcon;
  section?: string;
}

const emNav: NavItem[] = [
  {
    to: "/",
    label: "ダッシュボード",
    hint: "チーム全員の状況",
    icon: LayoutDashboard,
    section: "EM 向け",
  },
  {
    to: "/daily-pulse",
    label: "日報サマリー",
    hint: "AI 要約 + 履歴",
    icon: CalendarDays,
    section: "EM 向け",
  },
  {
    to: "/simulator",
    label: "組織シミュレーション",
    hint: "体制変更の影響を AI が整理",
    icon: Compass,
    section: "EM 向け",
  },
  {
    to: "/chat",
    label: "AI チャット",
    hint: "チームの状況について質問",
    icon: MessageSquare,
    section: "EM 向け",
  },
];

const adminNav: NavItem[] = [
  ...emNav,
  {
    to: "/admin",
    label: "管理",
    hint: "アカウント / 組織",
    icon: Settings2,
    section: "Admin",
  },
];

const memberNav: NavItem[] = [
  { to: "/me", label: "ホーム", icon: LayoutDashboard, section: "あなた" },
  { to: "/me/goals", label: "目標 / キャリア", icon: Target, section: "あなた" },
  { to: "/me/daily", label: "日報", icon: CalendarDays, section: "あなた" },
  { to: "/me/1on1s", label: "1on1 履歴", icon: MessageSquare, section: "あなた" },
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
    <AppShell user={user} navItems={navItems}>
      {isEmLike ? <EmRoutes isAdmin={isAdmin} /> : <MemberRoutes />}
    </AppShell>
  );
}

function AppShell({
  user,
  navItems,
  children,
}: {
  user: CurrentUser;
  navItems: NavItem[];
  children: React.ReactNode;
}) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();

  // Auto-close the mobile drawer on route change.
  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <DesktopSidebar user={user} navItems={navItems} />
      <MobileDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        user={user}
        navItems={navItems}
      />

      <div className="flex flex-col min-h-screen min-w-0">
        <Topbar
          user={user}
          onOpenMenu={() => setDrawerOpen(true)}
          currentPath={location.pathname}
          navItems={navItems}
        />
        <main className="flex-1 px-4 sm:px-6 lg:px-10 py-6 sm:py-8 max-w-[1440px] w-full mx-auto animate-slide-up">
          {children}
        </main>
        <Footer />
      </div>
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

function BrandBlock() {
  return (
    <div className="px-5 py-5 flex items-center gap-2.5">
      <span className="grid place-items-center w-9 h-9 rounded-xl bg-brand-gradient text-white shadow-pop">
        <Compass size={18} />
      </span>
      <div className="leading-tight">
        <div className="text-base font-bold tracking-tight text-slate-900">
          AtlasLens
        </div>
        <div className="text-[11px] text-slate-500">EM Co-pilot</div>
      </div>
    </div>
  );
}

function RoleBadge({ role }: { role: string }) {
  const label =
    role === "admin" ? "Admin" : role === "em" ? "EM-Copilot" : "メンバー";
  const tone =
    role === "admin"
      ? "bg-rose-100 text-rose-700 border-rose-200"
      : role === "em"
      ? "bg-brand/10 text-brand-dark border-brand/20"
      : "bg-slate-100 text-slate-600 border-slate-200";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-semibold border ${tone}`}
    >
      {label}
    </span>
  );
}

function SidebarNav({
  navItems,
  onItemClick,
}: {
  navItems: NavItem[];
  onItemClick?: () => void;
}) {
  // Group items by section.
  const sections = navItems.reduce<Record<string, NavItem[]>>((acc, item) => {
    const k = item.section ?? "ナビゲーション";
    (acc[k] ??= []).push(item);
    return acc;
  }, {});
  return (
    <nav className="px-2 pb-4 grid gap-0.5">
      {Object.entries(sections).map(([section, items]) => (
        <div key={section}>
          <div className="sidebar-section-label">{section}</div>
          {items.map((n) => {
            const Icon = n.icon;
            return (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/" || n.to === "/me"}
                onClick={onItemClick}
                className={({ isActive }) =>
                  `sidebar-link ${isActive ? "sidebar-link-active" : ""}`
                }
              >
                <Icon size={16} className="shrink-0" />
                <span className="truncate">{n.label}</span>
              </NavLink>
            );
          })}
        </div>
      ))}
    </nav>
  );
}

function SidebarUserCard({ user }: { user: CurrentUser }) {
  return (
    <div className="mt-auto border-t border-slate-200 p-4 grid gap-2">
      <div className="flex items-center gap-2.5">
        <span className="grid place-items-center w-9 h-9 rounded-full bg-brand/10 text-brand-dark font-semibold">
          {(user.profile?.name ?? user.name).slice(0, 1) || "A"}
        </span>
        <div className="min-w-0 leading-tight">
          <div className="text-sm font-semibold text-slate-900 truncate">
            {user.profile?.name ?? user.name}
          </div>
          <div className="text-[11px] text-slate-500 truncate">{user.email}</div>
        </div>
      </div>
      <div className="flex items-center justify-between gap-2">
        <RoleBadge role={user.role} />
        <button
          onClick={logout}
          className="text-xs text-slate-500 hover:text-rose-700 inline-flex items-center gap-1"
          title="ログアウト"
        >
          <LogOut size={12} /> ログアウト
        </button>
      </div>
    </div>
  );
}

function DesktopSidebar({
  user,
  navItems,
}: {
  user: CurrentUser;
  navItems: NavItem[];
}) {
  return (
    <aside className="sidebar">
      <BrandBlock />
      <SidebarNav navItems={navItems} />
      <SidebarUserCard user={user} />
    </aside>
  );
}

function MobileDrawer({
  open,
  onClose,
  user,
  navItems,
}: {
  open: boolean;
  onClose: () => void;
  user: CurrentUser;
  navItems: NavItem[];
}) {
  if (!open) return null;
  return (
    <div className="lg:hidden fixed inset-0 z-40 flex">
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-hidden
      />
      <aside className="relative w-72 max-w-[80%] h-full bg-white border-r border-slate-200 flex flex-col animate-slide-up">
        <div className="flex items-center justify-between px-3 py-2 border-b border-slate-100">
          <BrandBlock />
          <button
            onClick={onClose}
            className="p-2 rounded-md text-slate-500 hover:bg-slate-100"
            aria-label="メニューを閉じる"
          >
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto scroll-area">
          <SidebarNav navItems={navItems} onItemClick={onClose} />
        </div>
        <SidebarUserCard user={user} />
      </aside>
    </div>
  );
}

function Topbar({
  user,
  onOpenMenu,
  currentPath,
  navItems,
}: {
  user: CurrentUser;
  onOpenMenu: () => void;
  currentPath: string;
  navItems: NavItem[];
}) {
  const active =
    navItems.find(
      (n) =>
        n.to === currentPath ||
        (n.to !== "/" && n.to !== "/me" && currentPath.startsWith(n.to)),
    ) ??
    (currentPath === "/" ? navItems[0] : undefined);

  return (
    <header className="topbar">
      <button
        onClick={onOpenMenu}
        className="lg:hidden p-2 rounded-md text-slate-600 hover:bg-slate-100"
        aria-label="メニューを開く"
      >
        <Menu size={20} />
      </button>
      <div className="min-w-0 flex-1">
        <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
          {active?.section ?? "AtlasLens"}
        </div>
        <h1 className="text-sm sm:text-base font-semibold text-slate-900 truncate">
          {active?.label ?? "AtlasLens"}
        </h1>
      </div>
      <div className="flex items-center gap-2 lg:hidden">
        <span className="hidden sm:inline-flex items-center gap-1.5 text-xs text-slate-500">
          <User size={14} className="text-slate-400" />
          {user.profile?.name ?? user.name}
        </span>
        <button
          onClick={logout}
          className="p-2 rounded-md text-slate-500 hover:text-rose-700 hover:bg-slate-100"
          aria-label="ログアウト"
        >
          <LogOut size={16} />
        </button>
      </div>
      <div className="hidden lg:flex items-center gap-2">
        <Sparkles size={14} className="text-brand" />
        <span className="text-xs text-slate-500">AtlasLens</span>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-[1440px] px-4 sm:px-6 lg:px-10 py-3 text-xs text-slate-400 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
        <span>AtlasLens — EM Co-pilot powered by Azure AI Foundry</span>
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
