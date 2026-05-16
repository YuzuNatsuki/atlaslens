import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { meApi } from "@/lib/meApi";

const STATUS_TONE: Record<string, string> = {
  on_track: "bg-emerald-100 text-emerald-700",
  at_risk: "bg-amber-100 text-amber-700",
  off_track: "bg-rose-100 text-rose-700",
  done: "bg-slate-200 text-slate-700",
};

export default function MyDashboard() {
  const profileQ = useQuery({ queryKey: ["me", "profile"], queryFn: meApi.profile });
  const goalsQ = useQuery({ queryKey: ["me", "goals"], queryFn: meApi.goals });
  const dailyQ = useQuery({ queryKey: ["me", "daily"], queryFn: meApi.dailyReports });
  const oneOnOneQ = useQuery({ queryKey: ["me", "1on1s"], queryFn: meApi.oneOnOnes });

  const profile = profileQ.data;
  const lastDaily = dailyQ.data?.reports.slice(-1)[0];
  const nextActionable = oneOnOneQ.data?.one_on_ones.slice(-1)[0];

  return (
    <div className="grid gap-4 sm:gap-6">
      <section className="card">
        <h1 className="text-xl sm:text-2xl font-bold">
          {profile ? `${profile.name} さん、お疲れさまです` : "読み込み中..."}
        </h1>
        {profile && (
          <>
            <p className="text-slate-500">{profile.title}</p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {profile.skills.map((s) => (
                <span key={s} className="pill bg-brand/10 text-brand">
                  {s}
                </span>
              ))}
            </div>
          </>
        )}
      </section>

      <section>
        <div className="flex items-baseline justify-between mb-2">
          <h2 className="text-lg font-semibold">今期の目標</h2>
          <Link to="/me/goals" className="text-xs text-brand hover:underline">
            詳細を見る →
          </Link>
        </div>
        {goalsQ.isLoading && <p className="text-slate-500">読み込み中…</p>}
        <div className="grid gap-3">
          {goalsQ.data?.goals.map((g) => (
            <div key={g.id} className="card">
              <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1">
                <span className="font-medium">{g.objective}</span>
                <span className={`pill ${STATUS_TONE[g.status] ?? "bg-slate-100"}`}>
                  {g.status} · {g.progress_pct}%
                </span>
              </div>
              <ul className="mt-2 text-sm text-slate-700 list-disc ml-5">
                {g.key_results.map((kr, i) => (
                  <li key={i}>{kr}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="grid sm:grid-cols-2 gap-3 sm:gap-4">
        <Link to="/me/daily" className="card hover:shadow-md transition">
          <h3 className="font-semibold text-brand">最新の日報</h3>
          {lastDaily ? (
            <>
              <p className="text-xs text-slate-500 mt-1">{lastDaily.report_date}</p>
              <p className="text-sm mt-2 line-clamp-2">{lastDaily.today}</p>
            </>
          ) : (
            <p className="text-sm text-slate-500 mt-2">まだ提出した日報がありません</p>
          )}
          <p className="text-xs text-brand mt-3">日報を書く →</p>
        </Link>

        <Link to="/me/1on1s" className="card hover:shadow-md transition">
          <h3 className="font-semibold text-brand">直近の 1on1</h3>
          {nextActionable ? (
            <>
              <p className="text-xs text-slate-500 mt-1">
                {new Date(nextActionable.held_at).toLocaleDateString()}
              </p>
              <p className="text-sm mt-2 line-clamp-2">
                {(nextActionable.topics ?? []).join(" · ") || nextActionable.notes.slice(0, 80)}
              </p>
            </>
          ) : (
            <p className="text-sm text-slate-500 mt-2">1on1 履歴がまだありません</p>
          )}
          <p className="text-xs text-brand mt-3">履歴を見る →</p>
        </Link>
      </section>
    </div>
  );
}
