import { useParams, Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  CalendarCheck,
  ClipboardList,
  Compass,
  Sparkles,
  Target,
} from "lucide-react";

import { api, type Goal, type Insights } from "@/lib/api";
import { humanizeEvidenceId, pickEvidence, pickText } from "@/lib/format";
import {
  EmptyState,
  InlineAlert,
  PageHeader,
  SectionHeader,
  SkeletonCard,
} from "@/components/ui";

const OKR_STATUS: Record<string, { label: string; cls: string }> = {
  on_track: { label: "順調", cls: "pill-emerald" },
  at_risk: { label: "注意", cls: "pill-amber" },
  off_track: { label: "遅延", cls: "pill-rose" },
  done: { label: "完了", cls: "pill-slate" },
};

export default function MemberDetail() {
  const { id = "" } = useParams<{ id: string }>();
  const memberQ = useQuery({
    queryKey: ["member", id],
    queryFn: () => api.getMember(id),
    enabled: Boolean(id),
  });

  if (memberQ.isLoading) {
    return (
      <div className="grid gap-4">
        <SkeletonCard lines={3} />
        <SkeletonCard lines={2} />
        <SkeletonCard lines={4} />
      </div>
    );
  }
  if (memberQ.isError || !memberQ.data) {
    return (
      <InlineAlert tone="error">
        メンバー情報の取得に失敗しました: {(memberQ.error as Error)?.message ?? "不明なエラー"}
      </InlineAlert>
    );
  }

  const m = memberQ.data;

  return (
    <div className="grid gap-8">
      <div>
        <Link to="/" className="meta inline-flex items-center gap-1 hover:text-brand-dark">
          <ArrowLeft size={12} />
          チーム一覧に戻る
        </Link>
      </div>

      <PageHeader
        title={m.profile.name}
        subtitle={
          <>
            {m.profile.title} ・ 入社 {m.profile.joined_at}
          </>
        }
        actions={
          <Link to={`/one-on-ones/${m.profile.id}`} className="btn-primary">
            <CalendarCheck size={14} />
            1on1 を準備
          </Link>
        }
      />

      <section className="card">
        {m.profile.bio && (
          <p className="text-sm leading-relaxed text-slate-700">{m.profile.bio}</p>
        )}
        {m.profile.skills.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {m.profile.skills.map((s) => (
              <span key={s} className="pill-brand">
                {s}
              </span>
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionHeader
          icon={<Target size={16} className="text-brand" />}
          title="目標 (OKR + キャリアキャンバス)"
          subtitle="本人が MyGoals で記入した内容を読み取り専用で表示しています"
        />
        {m.goals.length === 0 ? (
          <EmptyState title="目標はまだ設定されていません" />
        ) : (
          <div className="grid gap-3">
            {m.goals.map((g) => (
              <GoalCardEm key={g.id} goal={g} />
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionHeader
          icon={<Sparkles size={16} className="text-brand" />}
          title="AI による状況整理"
          subtitle="Analyzer エージェント（Foundry Agent Service）が日報・OKR・1on1 履歴を横断参照します"
        />
        <InsightsPanel memberId={m.profile.id} />
      </section>

      <section>
        <SectionHeader
          icon={<ClipboardList size={16} className="text-brand" />}
          title="直近の日報"
        />
        {m.recent_daily_reports.length === 0 ? (
          <EmptyState title="日報はまだ記録されていません" />
        ) : (
          <div className="grid gap-2">
            {m.recent_daily_reports.map((r) => (
              <div key={r.id} className="card">
                <div className="flex items-baseline justify-between">
                  <span className="font-medium">{r.report_date}</span>
                  {r.blockers && <span className="pill-rose">課題あり</span>}
                </div>
                <p className="text-sm mt-2">
                  <span className="text-slate-400">昨日: </span>
                  {r.yesterday}
                </p>
                <p className="text-sm">
                  <span className="text-slate-400">今日: </span>
                  {r.today}
                </p>
                {r.blockers && (
                  <p className="text-sm text-rose-700">
                    <span className="text-slate-400">進められないこと: </span>
                    {r.blockers}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionHeader
          icon={<CalendarCheck size={16} className="text-brand" />}
          title="直近の 1on1"
        />
        {m.recent_one_on_ones.length === 0 ? (
          <EmptyState
            title="1on1 の記録はまだありません"
            action={
              <Link
                to={`/one-on-ones/${m.profile.id}`}
                className="btn-secondary"
              >
                最初の 1on1 を準備する
              </Link>
            }
          />
        ) : (
          <div className="grid gap-2">
            {m.recent_one_on_ones.map((o) => (
              <div key={o.id} className="card">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-medium">
                    {new Date(o.held_at).toLocaleString("ja-JP")}
                  </span>
                  <span className="meta truncate">{o.topics.join(" · ")}</span>
                </div>
                <p className="text-sm mt-2 whitespace-pre-wrap">{o.notes}</p>
                {o.todos.length > 0 && (
                  <ul className="mt-2 text-sm list-disc ml-5 grid gap-0.5">
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

function GoalCardEm({ goal }: { goal: Goal }) {
  const status = OKR_STATUS[goal.status] ?? { label: goal.status, cls: "pill-slate" };
  const hasCareer =
    !!goal.career_vision_1y ||
    !!goal.career_vision_3y ||
    (goal.skills_to_grow?.length ?? 0) > 0 ||
    (goal.roles_to_explore?.length ?? 0) > 0 ||
    !!goal.support_needed;
  return (
    <div className="card">
      <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1">
        <span className="font-medium text-slate-900">{goal.objective}</span>
        <div className="flex items-center gap-2 shrink-0">
          <span className="meta">{goal.period}</span>
          <span className={status.cls}>{status.label}</span>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <div className="flex-1 bg-slate-200 rounded-full h-1.5 overflow-hidden">
          <div
            className="bg-brand rounded-full h-1.5 transition-all"
            style={{ width: `${goal.progress_pct}%` }}
          />
        </div>
        <span className="text-xs text-slate-600 whitespace-nowrap">
          {goal.progress_pct}%
        </span>
      </div>
      {goal.key_results.length > 0 && (
        <ul className="mt-3 text-sm text-slate-700 list-disc ml-5 grid gap-0.5">
          {goal.key_results.map((kr, i) => (
            <li key={i}>{kr}</li>
          ))}
        </ul>
      )}

      {hasCareer && (
        <div className="mt-4 border-t border-slate-100 pt-3 grid gap-2.5">
          <p className="eyebrow flex items-center gap-1.5">
            <Compass size={12} /> キャリアキャンバス
          </p>
          {goal.career_vision_1y && (
            <CanvasRowEm label="1 年後のなりたい姿" value={goal.career_vision_1y} />
          )}
          {goal.career_vision_3y && (
            <CanvasRowEm label="3 年後のなりたい姿" value={goal.career_vision_3y} />
          )}
          {(goal.skills_to_grow?.length ?? 0) > 0 && (
            <div>
              <p className="label">伸ばしたいスキル</p>
              <div className="flex flex-wrap gap-1.5">
                {goal.skills_to_grow!.map((s) => (
                  <span key={s} className="pill-brand">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
          {(goal.roles_to_explore?.length ?? 0) > 0 && (
            <div>
              <p className="label">挑戦したいロール</p>
              <div className="flex flex-wrap gap-1.5">
                {goal.roles_to_explore!.map((s) => (
                  <span key={s} className="pill-slate">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
          {goal.support_needed && (
            <CanvasRowEm
              label="マネージャー / 周囲に求める支援"
              value={goal.support_needed}
            />
          )}
        </div>
      )}
    </div>
  );
}

function CanvasRowEm({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="label">{label}</p>
      <p className="text-sm text-slate-700 whitespace-pre-wrap">{value}</p>
    </div>
  );
}

function InsightsPanel({ memberId }: { memberId: string }) {
  const m = useMutation({ mutationFn: () => api.memberInsights(memberId) });
  const membersQ = useQuery({ queryKey: ["members"], queryFn: api.listMembers });
  const memberIndex: Record<string, string> = Object.fromEntries(
    (membersQ.data?.members ?? []).map((mb) => [mb.id, mb.name]),
  );

  return (
    <div className="grid gap-3">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <button
          onClick={() => m.mutate()}
          disabled={m.isPending}
          className="btn-primary"
        >
          <Sparkles size={14} />
          {m.isPending ? "AI 解析中… (約 10 秒)" : "状況を AI に整理させる"}
        </button>
        {m.isError && (
          <InlineAlert tone="error">
            {(m.error as Error).message || "Insights 取得に失敗しました"}
          </InlineAlert>
        )}
      </div>

      {m.data && (
        <div className="card animate-fade-in">
          <Insights insights={m.data.insights} memberIndex={memberIndex} />
        </div>
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
    return (
      <pre className="text-xs whitespace-pre-wrap text-slate-500">{insights.raw}</pre>
    );
  }
  return (
    <div className="grid md:grid-cols-2 gap-4">
      <InsightBlock
        title="できていること"
        items={insights.highlights}
        tone="text-emerald-700"
        memberIndex={memberIndex}
      />
      <InsightBlock
        title="注意したい点"
        items={insights.risks}
        tone="text-rose-700"
        memberIndex={memberIndex}
      />
      <InsightBlock
        title="成長の兆し"
        items={insights.growth_signals}
        tone="text-brand-dark"
        memberIndex={memberIndex}
      />
      <div>
        <h3 className="font-medium text-sm text-slate-600 mb-1">
          対話の切り口（1on1 で確認したい論点）
        </h3>
        <ul className="text-sm list-disc ml-5 grid gap-1">
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
      {(!items || items.length === 0) ? (
        <p className="text-xs text-slate-400 italic">該当なし</p>
      ) : (
        <ul className="text-sm list-disc ml-5 grid gap-1">
          {items.map((it, i) => {
            const evidence = pickEvidence(it);
            return (
              <li key={i}>
                {pickText(it)}
                {evidence.length > 0 && (
                  <span className="text-xs text-slate-400 ml-1">
                    （参照元:{" "}
                    {evidence
                      .map((id) => humanizeEvidenceId(id, memberIndex))
                      .join("、")}
                    ）
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
