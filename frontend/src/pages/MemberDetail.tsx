import { useParams, Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";

import { api, type Insights } from "@/lib/api";
import { humanizeEvidenceId, pickEvidence, pickText } from "@/lib/format";

const OKR_STATUS: Record<string, { label: string; cls: string }> = {
  on_track: { label: "順調", cls: "bg-emerald-100 text-emerald-700" },
  at_risk: { label: "注意", cls: "bg-amber-100 text-amber-700" },
  off_track: { label: "遅延", cls: "bg-rose-100 text-rose-700" },
  done: { label: "完了", cls: "bg-slate-200 text-slate-700" },
};

export default function MemberDetail() {
  const { id = "" } = useParams<{ id: string }>();
  const memberQ = useQuery({
    queryKey: ["member", id],
    queryFn: () => api.getMember(id),
    enabled: Boolean(id),
  });

  if (memberQ.isLoading) return <p className="text-slate-500">読み込み中…</p>;
  if (memberQ.isError || !memberQ.data) return <p className="text-rose-600">取得失敗</p>;

  const m = memberQ.data;

  return (
    <div className="grid gap-6">
      <div>
        <Link to="/" className="text-sm text-slate-500 hover:text-brand">← チーム一覧</Link>
      </div>

      <section className="card">
        <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold">{m.profile.name}</h1>
            <p className="text-slate-500">{m.profile.title}</p>
            <p className="text-xs text-slate-400 mt-1">入社: {m.profile.joined_at}</p>
          </div>
          <Link to={`/one-on-ones/${m.profile.id}`} className="btn-primary self-start">
            1on1 を準備
          </Link>
        </div>
        <p className="mt-3 text-sm">{m.profile.bio}</p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {m.profile.skills.map((s) => (
            <span key={s} className="pill bg-brand/10 text-brand">
              {s}
            </span>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-2">目標 (OKR)</h2>
        {m.goals.length === 0 ? (
          <p className="text-sm text-slate-400">目標はまだ設定されていません。</p>
        ) : (
          <div className="grid gap-3">
            {m.goals.map((g) => {
              const status = OKR_STATUS[g.status] ?? { label: g.status, cls: "bg-slate-100 text-slate-600" };
              return (
                <div key={g.id} className="card">
                  <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1">
                    <span className="font-medium">{g.objective}</span>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs text-slate-500">{g.period}</span>
                      <span className={`pill text-xs ${status.cls}`}>{status.label}</span>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 bg-slate-200 rounded-full h-1.5">
                      <div
                        className="bg-brand rounded-full h-1.5 transition-all"
                        style={{ width: `${g.progress_pct}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-600 whitespace-nowrap">{g.progress_pct}%</span>
                  </div>
                  <ul className="mt-2 text-sm text-slate-700 list-disc ml-5">
                    {g.key_results.map((kr, i) => (
                      <li key={i}>{kr}</li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold">AI による状況整理</h2>
          <InsightsTrigger memberId={m.profile.id} />
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-2">直近の日報</h2>
        {m.recent_daily_reports.length === 0 ? (
          <p className="text-sm text-slate-400">日報はまだ記録されていません。</p>
        ) : (
          <div className="grid gap-2">
            {m.recent_daily_reports.map((r) => (
              <div key={r.id} className="card">
                <div className="flex items-baseline justify-between">
                  <span className="font-medium">{r.report_date}</span>
                  {r.blockers && (
                    <span className="pill bg-rose-100 text-rose-700">ブロッカー</span>
                  )}
                </div>
                <p className="text-sm mt-2"><span className="text-slate-400">昨日: </span>{r.yesterday}</p>
                <p className="text-sm"><span className="text-slate-400">今日: </span>{r.today}</p>
                {r.blockers && (
                  <p className="text-sm text-rose-700"><span className="text-slate-400">ブロッカー: </span>{r.blockers}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-2">直近の 1on1</h2>
        {m.recent_one_on_ones.length === 0 ? (
          <p className="text-sm text-slate-400">
            1on1 の記録はまだありません。
            <Link to={`/one-on-ones/${m.profile.id}`} className="ml-1 text-brand hover:underline">
              最初の 1on1 を準備する →
            </Link>
          </p>
        ) : (
          <div className="grid gap-2">
            {m.recent_one_on_ones.map((o) => (
              <div key={o.id} className="card">
                <div className="flex items-baseline justify-between">
                  <span className="font-medium">{new Date(o.held_at).toLocaleString()}</span>
                  <span className="text-xs text-slate-500">{o.topics.join(" · ")}</span>
                </div>
                <p className="text-sm mt-2 whitespace-pre-wrap">{o.notes}</p>
                {o.todos.length > 0 && (
                  <ul className="mt-2 text-sm list-disc ml-5">
                    {o.todos.map((t, i) => (
                      <li key={i}>{t}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function InsightsTrigger({ memberId }: { memberId: string }) {
  const m = useMutation({ mutationFn: () => api.memberInsights(memberId) });
  const membersQ = useQuery({ queryKey: ["members"], queryFn: api.listMembers });
  const memberIndex: Record<string, string> = Object.fromEntries(
    (membersQ.data?.members ?? []).map((mb) => [mb.id, mb.name]),
  );

  return (
    <div className="grid gap-2 w-full sm:w-auto">
      <button
        onClick={() => m.mutate()}
        disabled={m.isPending}
        className="btn-primary flex items-center gap-1"
      >
        <Sparkles size={14} />
        {m.isPending ? "状況を AI に整理させています… (約 10 秒)" : "状況を AI に整理させる"}
      </button>
      {m.data && (
        <div className="card mt-2">
          <p className="text-xs text-slate-400 mb-3">
            Analyst エージェントによる状況整理（日報・OKR・1on1 履歴を参照）
          </p>
          <Insights insights={m.data.insights} memberIndex={memberIndex} />
        </div>
      )}
      {m.isError && (
        <p className="text-sm text-rose-700">
          {(m.error as Error).message || "失敗しました"}
        </p>
      )}
    </div>
  );
}

function Insights({
  insights,
  memberIndex,
}: {
  insights: Insights | undefined;
  memberIndex: Record<string, string>;
}) {
  if (!insights) return null;
  if (insights.parse_error) {
    return <pre className="text-xs whitespace-pre-wrap text-slate-500">{insights.raw}</pre>;
  }
  return (
    <div className="grid md:grid-cols-2 gap-4">
      <InsightBlock title="できていること" items={insights.highlights} tone="text-emerald-700" memberIndex={memberIndex} />
      <InsightBlock title="注意したい点" items={insights.risks} tone="text-rose-700" memberIndex={memberIndex} />
      <InsightBlock title="成長の兆し" items={insights.growth_signals} tone="text-brand" memberIndex={memberIndex} />
      <div>
        <h3 className="font-medium text-sm text-slate-500 mb-1">対話の切り口（1on1 で確認したい論点）</h3>
        <ul className="text-sm list-disc ml-5">
          {(insights.suggested_questions ?? []).map((q: unknown, i: number) => (
            <li key={i}>{pickText(q)}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function InsightBlock({
  title,
  items,
  tone,
  memberIndex,
}: {
  title: string;
  items?: unknown[];
  tone: string;
  memberIndex: Record<string, string>;
}) {
  return (
    <div>
      <h3 className={`font-medium text-sm mb-1 ${tone}`}>{title}</h3>
      <ul className="text-sm list-disc ml-5">
        {(items ?? []).map((it, i) => {
          const evidence = pickEvidence(it);
          return (
            <li key={i}>
              {pickText(it)}
              {evidence.length > 0 && (
                <span className="text-xs text-slate-400 ml-1">
                  (参照元: {evidence.map((id) => humanizeEvidenceId(id, memberIndex)).join("、")})
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
