import { useParams, Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";

import { api, type Insights } from "@/lib/api";
import { pickEvidence, pickText } from "@/lib/format";

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
        <div className="grid gap-3">
          {m.goals.map((g) => (
            <div key={g.id} className="card">
              <div className="flex items-baseline justify-between">
                <span className="font-medium">{g.objective}</span>
                <span className="text-xs text-slate-500">
                  {g.period} · {g.status} · {g.progress_pct}%
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

      <section>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold">AI による状況整理</h2>
          <InsightsTrigger memberId={m.profile.id} />
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-2">直近の日報</h2>
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
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-2">直近の 1on1</h2>
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
      </section>
    </div>
  );
}

function InsightsTrigger({ memberId }: { memberId: string }) {
  const m = useMutation({ mutationFn: () => api.memberInsights(memberId) });
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
          <Insights insights={m.data.insights} />
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

function Insights({ insights }: { insights: Insights | undefined }) {
  if (!insights) return null;
  if (insights.parse_error) {
    return <pre className="text-xs whitespace-pre-wrap text-slate-500">{insights.raw}</pre>;
  }
  return (
    <div className="grid md:grid-cols-2 gap-4">
      <InsightBlock title="できていること" items={insights.highlights} tone="text-emerald-700" />
      <InsightBlock title="注意したい点" items={insights.risks} tone="text-rose-700" />
      <InsightBlock title="成長の兆し" items={insights.growth_signals} tone="text-brand" />
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
}: {
  title: string;
  items?: unknown[];
  tone: string;
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
                  (参照元: {evidence.join(", ")})
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
