import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  Calendar,
  MessageSquare,
  ShieldCheck,
  Users,
} from "lucide-react";

import { api } from "@/lib/api";
import { EmptyState, PageHeader, SectionHeader, SkeletonCard } from "@/components/ui";

const ROLE_LABEL: Record<string, string> = {
  em: "EM",
  tech_lead: "テックリード",
  senior: "シニア",
  mid: "ミドル",
  junior: "ジュニア",
  admin: "Admin",
};

function oneOnOneTone(days: number | null): { cls: string; label: string } {
  if (days === null) return { cls: "text-slate-400", label: "未実施" };
  if (days >= 30) return { cls: "text-rose-700 font-semibold", label: `${days}日前` };
  if (days >= 14) return { cls: "text-amber-700", label: `${days}日前` };
  return { cls: "text-slate-500", label: `${days}日前` };
}

export default function Dashboard() {
  const membersQ = useQuery({ queryKey: ["members"], queryFn: api.listMembers });
  const healthQ = useQuery({ queryKey: ["team-health"], queryFn: api.teamHealth });

  return (
    <div className="grid gap-8">
      <PageHeader
        title="ダッシュボード"
        subtitle="チーム（アトラス株式会社）の最新スナップショット"
      />

      <section>
        <SectionHeader
          icon={<Users size={16} className="text-brand" />}
          title="チーム一覧"
          subtitle="カードをクリックすると個人ページへ"
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {membersQ.isLoading &&
            Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} lines={2} />)}
          {membersQ.data?.members.map((m) => (
            <Link
              key={m.id}
              to={`/members/${m.id}`}
              className="card hover:shadow-pop hover:border-brand/40 transition group"
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-semibold text-slate-900 truncate group-hover:text-brand-dark">
                  {m.name}
                </span>
                <span className="pill-slate shrink-0">{ROLE_LABEL[m.role] ?? m.role}</span>
              </div>
              <p className="text-sm text-slate-500 mt-1 truncate">{m.title}</p>
              {m.skills.length > 0 && (
                <p className="text-xs text-slate-400 mt-3 truncate">
                  スキル: {m.skills.slice(0, 4).join(" · ")}
                </p>
              )}
            </Link>
          ))}
          {!membersQ.isLoading && membersQ.data?.members.length === 0 && (
            <div className="sm:col-span-2 lg:col-span-3">
              <EmptyState
                icon={<Users size={28} />}
                title="メンバーがまだ登録されていません"
                description="管理ページからアカウントを作成すると、ここに表示されます。"
              />
            </div>
          )}
        </div>
      </section>

      <section>
        <SectionHeader
          icon={<ShieldCheck size={16} className="text-brand" />}
          title="チームコンディション"
          subtitle="観察事実のみ。AI は感情や評価を推測しません"
          actions={
            <Link to="/chat" className="btn-ghost btn-xs hidden sm:inline-flex">
              <MessageSquare size={12} />
              AI に深掘りを依頼
            </Link>
          }
        />
        <div className="grid gap-2">
          {healthQ.isLoading &&
            Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} lines={1} />)}
          {healthQ.data?.members.map((row) => {
            const tone = oneOnOneTone(row.days_since_last_one_on_one);
            const overdue =
              row.days_since_last_one_on_one !== null &&
              row.days_since_last_one_on_one >= 30;
            return (
              <div
                key={row.member_id}
                className={`card transition ${overdue ? "border-rose-200" : ""}`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <Link
                      to={`/members/${row.member_id}`}
                      className="font-medium text-slate-900 hover:text-brand-dark hover:underline"
                    >
                      {row.name}
                    </Link>
                    <div className="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                      <span className="inline-flex items-center gap-1">
                        <Calendar size={12} className="text-slate-400" />
                        日報 {row.daily_reports_last_14d}/14d
                      </span>
                      <span>ブロッカー言及 {row.blockers_mentioned_last_14d}</span>
                      <span>会議参加 {row.meetings_attended_last_14d}</span>
                      <span className={tone.cls}>
                        前回 1on1 {tone.label}
                        {overdue && " ⚠"}
                      </span>
                    </div>
                  </div>
                  {row.facts_for_em.length > 0 && (
                    <ul className="grid gap-1 text-xs text-slate-600 max-w-md">
                      {row.facts_for_em.slice(0, 3).map((f, i) => (
                        <li key={i} className="inline-flex items-start gap-1">
                          <AlertCircle
                            size={12}
                            className={overdue ? "text-rose-500 mt-0.5" : "text-amber-500 mt-0.5"}
                          />
                          <span>{f}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            );
          })}
          {healthQ.data?.members.length === 0 && !healthQ.isLoading && (
            <EmptyState
              title="観察対象がありません"
              description="メンバーを登録すると、行動データから注意点を整理します。"
            />
          )}
        </div>
      </section>
    </div>
  );
}
