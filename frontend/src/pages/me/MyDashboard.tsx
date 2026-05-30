import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays, MessageSquare, Target } from "lucide-react";

import { meApi } from "@/lib/meApi";
import {
  EmptyState,
  PageHeader,
  SectionHeader,
  SkeletonCard,
} from "@/components/ui";

const STATUS_TONE: Record<string, string> = {
  on_track: "pill-emerald",
  at_risk: "pill-amber",
  off_track: "pill-rose",
  done: "pill-slate",
};

const STATUS_LABEL: Record<string, string> = {
  on_track: "順調",
  at_risk: "注意",
  off_track: "遅延",
  done: "完了",
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
    <div className="grid gap-8">
      <PageHeader
        title={profile ? `${profile.name} さん、お疲れさまです` : "読み込み中…"}
        subtitle={profile?.title}
      />

      {profile && profile.skills.length > 0 && (
        <section className="card">
          <p className="eyebrow mb-2">スキル</p>
          <div className="flex flex-wrap gap-1.5">
            {profile.skills.map((s) => (
              <span key={s} className="pill-brand">
                {s}
              </span>
            ))}
          </div>
        </section>
      )}

      <section>
        <SectionHeader
          icon={<Target size={16} className="text-brand" />}
          title="今期の目標"
          actions={
            <Link to="/me/goals" className="btn-ghost btn-xs">
              詳細を見る
            </Link>
          }
        />
        {goalsQ.isLoading && <SkeletonCard lines={3} />}
        {!goalsQ.isLoading && goalsQ.data?.goals.length === 0 && (
          <EmptyState title="目標はまだ設定されていません" />
        )}
        <div className="grid gap-3">
          {goalsQ.data?.goals.map((g) => (
            <div key={g.id} className="card">
              <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1">
                <span className="font-medium text-slate-900">{g.objective}</span>
                <span className={STATUS_TONE[g.status] ?? "pill-slate"}>
                  {STATUS_LABEL[g.status] ?? g.status} · {g.progress_pct}%
                </span>
              </div>
              <ul className="mt-2 text-sm text-slate-700 list-disc ml-5 grid gap-0.5">
                {g.key_results.map((kr, i) => (
                  <li key={i}>{kr}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="grid sm:grid-cols-2 gap-3 sm:gap-4">
        <Link
          to="/me/daily"
          className="card hover:shadow-pop hover:border-brand/30 transition group"
        >
          <h3 className="section-title">
            <CalendarDays size={16} className="text-brand" />
            最新の日報
          </h3>
          {lastDaily ? (
            <>
              <p className="meta mt-1">{lastDaily.report_date}</p>
              <p className="text-sm mt-2 line-clamp-2">{lastDaily.today}</p>
            </>
          ) : (
            <p className="empty-state mt-2">まだ提出した日報がありません</p>
          )}
          <p className="text-xs text-brand-dark mt-3 group-hover:underline">
            日報を書く →
          </p>
        </Link>

        <Link
          to="/me/1on1s"
          className="card hover:shadow-pop hover:border-brand/30 transition group"
        >
          <h3 className="section-title">
            <MessageSquare size={16} className="text-brand" />
            直近の 1on1
          </h3>
          {nextActionable ? (
            <>
              <p className="meta mt-1">
                {new Date(nextActionable.held_at).toLocaleDateString("ja-JP")}
              </p>
              <p className="text-sm mt-2 line-clamp-2">
                {(nextActionable.topics ?? []).join(" · ") ||
                  nextActionable.notes.slice(0, 80)}
              </p>
            </>
          ) : (
            <p className="empty-state mt-2">1on1 履歴がまだありません</p>
          )}
          <p className="text-xs text-brand-dark mt-3 group-hover:underline">
            履歴を見る →
          </p>
        </Link>
      </section>
    </div>
  );
}
