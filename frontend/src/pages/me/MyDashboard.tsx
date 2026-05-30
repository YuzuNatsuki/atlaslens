import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarDays,
  CheckCircle2,
  History,
  MessageSquare,
  RefreshCw,
  Sparkles,
  Target,
  TrendingUp,
  Wand2,
} from "lucide-react";

import { meApi, type GrowthSummary, type GrowthSummaryResponse } from "@/lib/meApi";
import {
  EmptyState,
  InlineAlert,
  SectionHeader,
  SkeletonCard,
  Spinner,
  formatJpDate,
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
    <div className="grid gap-8 animate-fade-in">
      <section className="hero">
        <div className="hero-content flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div className="min-w-0">
            <div className="text-xs uppercase tracking-[0.18em] opacity-80">
              {new Date().toLocaleDateString("ja-JP", {
                year: "numeric",
                month: "long",
                day: "numeric",
                weekday: "long",
              })}
            </div>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight mt-1">
              {profile ? `${profile.name} さん` : "読み込み中…"}
            </h1>
            {profile?.title && (
              <p className="text-sm opacity-90 mt-1">{profile.title}</p>
            )}
          </div>
          {profile && profile.skills.length > 0 && (
            <div className="flex flex-wrap gap-1.5 max-w-md">
              {profile.skills.slice(0, 8).map((s) => (
                <span
                  key={s}
                  className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-white/15 border border-white/20 text-white"
                >
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      </section>

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
        <Link to="/me/daily" className="card card-hover group">
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

        <Link to="/me/1on1s" className="card card-hover group">
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

      <GrowthSummarySection />
    </div>
  );
}

// ============================================================
// Skill Growth Summary — per-member AI benefit
// ============================================================

function GrowthSummarySection() {
  const qc = useQueryClient();
  const latestQ = useQuery({
    queryKey: ["me", "growth", "latest"],
    queryFn: meApi.latestGrowthSummary,
    refetchOnWindowFocus: false,
  });
  const historyQ = useQuery({
    queryKey: ["me", "growth", "history"],
    queryFn: meApi.listGrowthHistory,
    refetchOnWindowFocus: false,
  });
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [activeOverride, setActiveOverride] = useState<GrowthSummaryResponse | null>(null);

  const generateM = useMutation({
    mutationFn: (force: boolean) =>
      meApi.generateGrowthSummary({ force }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["me", "growth"] });
      setActiveKey(res.key ?? null);
      setActiveOverride(res);
    },
  });

  const openHistory = async (key: string) => {
    setActiveKey(key);
    setActiveOverride(null);
    try {
      const res = await meApi.getGrowthByKey(key);
      setActiveOverride(res);
    } catch {
      // swallow — UI shows the latest as fallback
    }
  };

  const visible: GrowthSummaryResponse | null =
    activeOverride ?? latestQ.data ?? null;
  const summary: GrowthSummary | null = visible?.summary ?? null;

  return (
    <section>
      <SectionHeader
        icon={<Sparkles size={16} className="text-brand" />}
        title="My Growth — AI による成長サマリー"
        subtitle="あなた本人の日報と目標だけを材料に、伸びている点と次の一歩を整理します"
        actions={
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => generateM.mutate(false)}
              disabled={generateM.isPending}
              className="btn-primary btn-xs"
              title="今日のサマリーが既にあれば再利用、なければ生成します"
            >
              <Wand2 size={12} />
              {generateM.isPending ? "生成中…" : "今日のサマリー"}
            </button>
            <button
              onClick={() => generateM.mutate(true)}
              disabled={generateM.isPending}
              className="btn-ghost btn-xs"
              title="今日の保存済みサマリーを上書きして AI に作り直させます"
            >
              <RefreshCw size={12} />
              再生成
            </button>
          </div>
        }
      />

      {generateM.isError && (
        <InlineAlert tone="error">
          {(generateM.error as Error).message || "サマリーの生成に失敗しました"}
        </InlineAlert>
      )}

      {latestQ.isLoading ? (
        <SkeletonCard lines={4} />
      ) : !summary ? (
        <EmptyState
          icon={<Sparkles size={28} />}
          title="まだ My Growth サマリーがありません"
          description="ボタンを押すと、直近 30 日分の日報と今の目標を元に AI が振り返りを作ります。"
          action={
            <button
              onClick={() => generateM.mutate(false)}
              disabled={generateM.isPending}
              className="btn-primary btn-xs"
            >
              <Wand2 size={12} /> 最初のサマリーを作る
            </button>
          }
        />
      ) : (
        <GrowthSummaryCard
          response={visible!}
          summary={summary}
          generating={generateM.isPending}
        />
      )}

      {historyQ.data && historyQ.data.items.length > 0 && (
        <div className="mt-4">
          <p className="eyebrow flex items-center gap-1.5 mb-2">
            <History size={12} /> 過去のサマリー
          </p>
          <div className="flex flex-wrap gap-1.5">
            {historyQ.data.items.map((it) => {
              const isActive = activeKey === it.key;
              return (
                <button
                  key={it.key}
                  onClick={() => openHistory(it.key)}
                  className={`px-2 py-1 rounded-full text-xs border transition ${
                    isActive
                      ? "bg-brand text-white border-brand"
                      : "bg-white text-slate-600 border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  {it.date}
                  {it.report_count != null && (
                    <span className="ml-1 opacity-70">({it.report_count}件)</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}

function GrowthSummaryCard({
  response,
  summary,
  generating,
}: {
  response: GrowthSummaryResponse;
  summary: GrowthSummary;
  generating: boolean;
}) {
  if (summary.parse_error) {
    return (
      <div className="card border-rose-200">
        <p className="text-sm text-rose-700 mb-2">
          サマリーの読み取りに失敗しました。以下に AI の返答をそのまま表示します。
        </p>
        <pre className="text-xs whitespace-pre-wrap text-slate-500 max-h-80 overflow-auto scroll-area">
          {summary.raw}
        </pre>
      </div>
    );
  }
  return (
    <article className="card grid gap-4">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="min-w-0">
          {summary.tldr && (
            <p className="text-sm text-slate-800 leading-relaxed">
              <span className="pill-brand mr-1.5">TL;DR</span>
              {summary.tldr}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500 shrink-0">
          {response.from_cache && (
            <span className="pill-slate">
              <CheckCircle2 size={10} /> 保存済み
            </span>
          )}
          {response.generated_at && (
            <span>生成 {formatJpDate(response.generated_at)}</span>
          )}
          {response.report_count != null && (
            <span>日報 {response.report_count} 件</span>
          )}
          {generating && <Spinner />}
        </div>
      </header>

      <div className="grid md:grid-cols-2 gap-3">
        <GrowthList
          title="伸びている領域"
          tone="text-emerald-700"
          items={(summary.growing ?? []).map((g) => ({
            heading: g.area,
            evidence: g.evidence,
            cta: g.next_step,
            ctaLabel: "次の一歩",
          }))}
          emptyLabel="該当なし — 日報が増えるとここに反映されます"
          icon={<TrendingUp size={14} className="text-emerald-600" />}
        />
        <GrowthList
          title="伸び悩んでいる領域"
          tone="text-amber-700"
          items={(summary.stuck ?? []).map((s) => ({
            heading: s.area,
            evidence: s.evidence,
            cta: s.suggested_action,
            ctaLabel: "とれる行動",
          }))}
          emptyLabel="目立った停滞は見当たりません"
          icon={<RefreshCw size={14} className="text-amber-600" />}
        />
      </div>

      {summary.career_alignment && (
        <div className="border-t border-slate-100 pt-3">
          <p className="eyebrow mb-1">キャリア目標との整合</p>
          <p className="text-sm text-slate-700 leading-relaxed">
            {summary.career_alignment}
          </p>
        </div>
      )}

      {(summary.recommended_focus?.length ?? 0) > 0 && (
        <div className="border-t border-slate-100 pt-3">
          <p className="eyebrow mb-1">今週のフォーカス候補</p>
          <ul className="text-sm list-disc ml-5 grid gap-1 text-slate-700">
            {summary.recommended_focus!.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}

function GrowthList({
  title,
  tone,
  items,
  emptyLabel,
  icon,
}: {
  title: string;
  tone: string;
  items: Array<{ heading: string; evidence: string; cta: string; ctaLabel: string }>;
  emptyLabel: string;
  icon: React.ReactNode;
}) {
  return (
    <div>
      <h3 className={`section-title text-sm ${tone}`}>
        {icon} {title}
      </h3>
      {items.length === 0 ? (
        <p className="empty-state mt-2">{emptyLabel}</p>
      ) : (
        <ul className="mt-2 grid gap-2.5">
          {items.map((it, i) => (
            <li key={i} className="grid gap-1">
              <p className="text-sm font-medium text-slate-800">{it.heading}</p>
              {it.evidence && (
                <p className="text-xs text-slate-500">{it.evidence}</p>
              )}
              {it.cta && (
                <p className="text-xs text-brand-dark">
                  <span className="opacity-70">{it.ctaLabel}: </span>
                  {it.cta}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
