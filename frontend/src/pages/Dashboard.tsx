import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/lib/api";

const ROLE_LABEL: Record<string, string> = {
  em: "EM",
  tech_lead: "テックリード",
  senior: "シニア",
  mid: "ミドル",
  junior: "ジュニア",
  admin: "Admin",
};

function oneOnOneDaysClass(days: number | null): string {
  if (days === null) return "text-slate-500";
  if (days >= 30) return "text-rose-600 font-semibold";
  if (days >= 14) return "text-amber-600";
  return "text-slate-500";
}

export default function Dashboard() {
  const membersQ = useQuery({ queryKey: ["members"], queryFn: api.listMembers });
  const healthQ = useQuery({ queryKey: ["team-health"], queryFn: api.teamHealth });

  return (
    <div className="grid gap-6">
      <section>
        <h2 className="text-lg font-semibold mb-3">チーム（アトラス株式会社）</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {membersQ.isLoading && <p className="text-slate-500">読み込み中…</p>}
          {membersQ.data?.members.map((m) => (
            <Link
              key={m.id}
              to={`/members/${m.id}`}
              className="card hover:shadow-md hover:border-brand/30 transition cursor-pointer"
            >
              <div className="flex items-baseline justify-between">
                <span className="font-semibold">{m.name}</span>
                <span className="pill bg-slate-100 text-slate-600">
                  {ROLE_LABEL[m.role] ?? m.role}
                </span>
              </div>
              <p className="text-sm text-slate-500 mt-1">{m.title}</p>
              <p className="text-xs text-slate-400 mt-2 truncate">
                {m.skills.slice(0, 4).join(" · ")}
              </p>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">チームコンディション（観察事実のみ）</h2>
        {healthQ.isLoading && <p className="text-slate-500">読み込み中…</p>}
        <div className="grid gap-2">
          {healthQ.data?.members.map((row) => (
            <div key={row.member_id} className="card">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/members/${row.member_id}`}
                    className="font-medium hover:underline hover:text-brand"
                  >
                    {row.name}
                  </Link>
                  <div className="text-xs mt-1 sm:mt-0 sm:ml-3 sm:inline">
                    <span className="text-slate-500">
                      日報 {row.daily_reports_last_14d}/14d ·
                      ブロッカー {row.blockers_mentioned_last_14d} ·
                      会議 {row.meetings_attended_last_14d}
                    </span>
                    {row.days_since_last_one_on_one !== null && (
                      <span className={`ml-1 ${oneOnOneDaysClass(row.days_since_last_one_on_one)}`}>
                        · 前回1on1 {row.days_since_last_one_on_one}日前
                        {row.days_since_last_one_on_one >= 30 && " ⚠"}
                      </span>
                    )}
                  </div>
                </div>
                <Link
                  to={`/one-on-ones/${row.member_id}`}
                  className="btn-primary self-start sm:self-auto"
                >
                  1on1 準備
                </Link>
              </div>
              {row.facts_for_em.length > 0 && (
                <ul className="mt-2 text-sm text-amber-700 list-disc ml-5">
                  {row.facts_for_em.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-400">
          ※ AtlasLens は感情やメンタル状態を推測しません。客観的な行動指標のみを EM 向けに提示します。
        </p>
      </section>
    </div>
  );
}
