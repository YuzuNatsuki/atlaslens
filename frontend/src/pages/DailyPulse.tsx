import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CalendarDays,
  CalendarRange,
  Compass,
  History,
  Lightbulb,
  RefreshCw,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Users,
} from "lucide-react";

import {
  api,
  type PastTeamSummary,
  type RangeMemberTrend,
  type RangeRiskSignal,
} from "@/lib/api";
import { pickText } from "@/lib/format";
import {
  EmptyState,
  InlineAlert,
  PageHeader,
  SectionHeader,
  SkeletonCard,
  Spinner,
  formatJpDate,
} from "@/components/ui";

const DEFAULT_DATE = "2026-05-19";
const DEFAULT_RANGE_START = "2026-05-13";
const DEFAULT_RANGE_END = "2026-05-19";

type Mode = "single" | "range";

export default function DailyPulsePage() {
  const [mode, setMode] = useState<Mode>("single");

  return (
    <div className="grid gap-8">
      <PageHeader
        title="日報サマリー"
        subtitle="Reporter エージェントがチーム全員の日報を読み、朝会前 30 秒で把握できる形に要約します。単日でも、期間（週次トレンド）でも生成できます。"
      />

      <div className="flex items-center gap-2">
        <ModeTab
          icon={<CalendarDays size={14} />}
          label="単日サマリー"
          active={mode === "single"}
          onClick={() => setMode("single")}
        />
        <ModeTab
          icon={<CalendarRange size={14} />}
          label="期間トレンド"
          active={mode === "range"}
          onClick={() => setMode("range")}
        />
      </div>

      {mode === "single" ? <SingleDayPanel /> : <RangePanel />}
    </div>
  );
}

function ModeTab({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs border transition ${
        active
          ? "bg-brand text-white border-brand shadow-sm"
          : "bg-white text-slate-700 border-slate-300 hover:bg-slate-100 hover:border-slate-400"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

// ============================ SINGLE DAY ============================

function SingleDayPanel() {
  const [reportDate, setReportDate] = useState<string>(DEFAULT_DATE);
  const qc = useQueryClient();

  const summaryQ = useQuery({
    queryKey: ["team-summary", reportDate],
    queryFn: () => api.teamSummary(reportDate),
    enabled: Boolean(reportDate),
  });

  const historyQ = useQuery({
    queryKey: ["team-summaries"],
    queryFn: api.listTeamSummaries,
    staleTime: 30_000,
  });

  const regenerateM = useMutation({
    mutationFn: () => api.regenerateTeamSummary(reportDate),
    onSuccess: (data) => {
      qc.setQueryData(["team-summary", reportDate], data);
      qc.invalidateQueries({ queryKey: ["team-summaries"] });
    },
  });

  useEffect(() => {
    regenerateM.reset();
  }, [reportDate]); // eslint-disable-line react-hooks/exhaustive-deps

  const sortedHistory = useMemo<PastTeamSummary[]>(() => {
    return (historyQ.data?.summaries ?? []).slice().sort((a, b) => {
      const da = a.generated_at ?? "";
      const db = b.generated_at ?? "";
      return db.localeCompare(da);
    });
  }, [historyQ.data]);

  const generating = summaryQ.isFetching || regenerateM.isPending;
  const summary = summaryQ.data;
  const hasResults = Boolean(summary?.summary);
  const fromCache = summary?.from_cache;

  return (
    <>
      <section className="card">
        <SectionHeader
          icon={<CalendarDays size={16} className="text-brand" />}
          title="日付を選んでサマリーを表示"
          subtitle="初回生成は 5〜10 秒、以降はキャッシュから瞬時に返ります"
        />
        <div className="flex flex-wrap items-end gap-3 mt-2">
          <label className="grid gap-1">
            <span className="label">対象日</span>
            <input
              type="date"
              value={reportDate}
              onChange={(e) => setReportDate(e.target.value)}
              className="input-sm"
            />
          </label>
          <button
            onClick={() => regenerateM.mutate()}
            disabled={generating || !reportDate}
            className="btn-secondary"
          >
            <RefreshCw size={14} className={regenerateM.isPending ? "animate-spin" : ""} />
            {regenerateM.isPending ? "AI 再生成中…" : hasResults ? "再生成" : "AI で生成"}
          </button>
          {fromCache && hasResults && !regenerateM.isPending && (
            <span className="pill-emerald" title={summary?.generated_at ?? undefined}>
              キャッシュから表示中
              {summary?.generated_at ? ` · ${formatJpDate(summary.generated_at)}` : ""}
            </span>
          )}
        </div>

        {regenerateM.isError && (
          <div className="mt-3">
            <InlineAlert tone="error">
              再生成に失敗しました: {(regenerateM.error as Error).message}
            </InlineAlert>
          </div>
        )}
      </section>

      <section className="grid gap-3">
        {summaryQ.isLoading && <SkeletonCard lines={4} />}
        {!summaryQ.isLoading && summaryQ.isError && (
          <InlineAlert tone="error">
            サマリーの取得に失敗しました: {(summaryQ.error as Error).message}
          </InlineAlert>
        )}
        {!summaryQ.isLoading && !hasResults && !regenerateM.isPending && (
          <EmptyState
            icon={<CalendarDays size={28} />}
            title="この日付のサマリーはまだ生成されていません"
            description="「AI で生成」を押すと Reporter エージェントが日報を読み込みます。"
          />
        )}
        {regenerateM.isPending && <Spinner label="Reporter エージェントが日報を読み込んでいます…" />}

        {hasResults && (
          <>
            <p className="meta">
              {summary?.report_count ?? 0} 名分の日報（{reportDate}）から作成
              {summary?.generated_at && (
                <> ・ 生成 {formatJpDate(summary.generated_at)}</>
              )}
            </p>

            {summary?.summary?.tldr && (
              <div className="card bg-gradient-to-br from-brand/5 to-transparent border-brand/20">
                <h3 className="section-title text-brand-dark mb-2">
                  <Sparkles size={16} className="text-brand" /> 今日のひと言サマリー
                </h3>
                <ul className="list-disc ml-5 text-sm grid gap-1">
                  {summary.summary.tldr.map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ul>
              </div>
            )}

            {summary?.summary?.highlights && (
              <div className="card">
                <h3 className="section-title mb-2">
                  <Users size={16} className="text-brand" /> メンバーごとの動き
                </h3>
                <ul className="grid gap-2 text-sm">
                  {Object.entries(summary.summary.highlights).map(([k, v]) => (
                    <li key={k} className="flex gap-2">
                      <span className="pill-brand shrink-0">{k}</span>
                      <span className="text-slate-700">{pickText(v)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {summary?.summary?.blockers_to_surface && (
              <div className="card border-amber-200 bg-amber-50/40">
                <h3 className="section-title text-amber-800 mb-2">
                  <AlertTriangle size={16} className="text-amber-600" />{" "}
                  EM が今日声をかけたい人
                </h3>
                <ul className="grid gap-2 text-sm">
                  {Object.entries(summary.summary.blockers_to_surface).map(([k, v]) => (
                    <li key={k} className="flex gap-2">
                      <span className="pill-amber shrink-0">{k}</span>
                      <span className="text-slate-800">{pickText(v)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {summary?.summary?.themes && summary.summary.themes.length > 0 && (
              <div className="card">
                <h3 className="section-title mb-2">
                  <Compass size={16} className="text-brand" /> チーム全体の傾向
                </h3>
                <ul className="list-disc ml-5 text-sm grid gap-1 text-slate-700">
                  {summary.summary.themes.map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </section>

      <section>
        <SectionHeader
          icon={<History size={16} className="text-brand" />}
          title="過去に生成したサマリー"
          subtitle="日付をクリックすると即座に表示します（Cosmos DB に永続化）"
        />
        {historyQ.isLoading && <SkeletonCard lines={3} />}
        {!historyQ.isLoading && sortedHistory.length === 0 && (
          <EmptyState
            title="まだ生成履歴がありません"
            description="生成すると、ここに新しい日付が追加されます。"
          />
        )}
        {sortedHistory.length > 0 && (
          <ul className="grid gap-2">
            {sortedHistory.map((row) => {
              const active = row.date === reportDate;
              return (
                <li key={row.date}>
                  <button
                    onClick={() => row.date && setReportDate(row.date)}
                    className={`w-full text-left card-tight transition flex items-center justify-between
                                ${active ? "border-brand/40 bg-brand/5" : "hover:border-brand/30 hover:bg-slate-50"}`}
                  >
                    <span className="font-medium text-slate-800">
                      {row.date}
                    </span>
                    <span className="text-xs text-slate-500 flex items-center gap-3">
                      {row.report_count !== undefined && row.report_count !== null && (
                        <span>{row.report_count} 件の日報</span>
                      )}
                      {row.generated_at && <span>{formatJpDate(row.generated_at)}</span>}
                      {active && <span className="pill-brand">表示中</span>}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </>
  );
}

// ============================ RANGE ============================

const TREND_STYLES: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
  "良化": {
    label: "良化",
    cls: "bg-emerald-100 text-emerald-700 border-emerald-200",
    icon: <TrendingUp size={11} />,
  },
  "停滞": {
    label: "停滞",
    cls: "bg-slate-100 text-slate-600 border-slate-200",
    icon: <TrendingDown size={11} className="rotate-90" />,
  },
  "悪化": {
    label: "悪化",
    cls: "bg-rose-100 text-rose-700 border-rose-200",
    icon: <TrendingDown size={11} />,
  },
  "不変": {
    label: "不変",
    cls: "bg-slate-100 text-slate-600 border-slate-200",
    icon: <TrendingDown size={11} className="rotate-90" />,
  },
};

const RISK_KIND_META: Record<string, { label: string; emoji: string; cls: string }> = {
  retention: { label: "離職リスク", emoji: "🚨", cls: "bg-rose-100 text-rose-700 border-rose-200" },
  friction: { label: "対人摩擦", emoji: "⚡", cls: "bg-amber-100 text-amber-700 border-amber-200" },
  capacity: { label: "過負荷", emoji: "🔥", cls: "bg-orange-100 text-orange-700 border-orange-200" },
  engagement: { label: "エンゲージメント低下", emoji: "💭", cls: "bg-amber-100 text-amber-700 border-amber-200" },
  health: { label: "コンディション", emoji: "🫧", cls: "bg-sky-100 text-sky-700 border-sky-200" },
};

function RangePanel() {
  const [start, setStart] = useState<string>(DEFAULT_RANGE_START);
  const [end, setEnd] = useState<string>(DEFAULT_RANGE_END);
  const qc = useQueryClient();

  const summaryQ = useQuery({
    queryKey: ["team-summary-range", start, end],
    queryFn: () => api.teamSummaryRange(start, end),
    enabled: Boolean(start) && Boolean(end),
  });

  const historyQ = useQuery({
    queryKey: ["team-summaries-range"],
    queryFn: api.listTeamSummariesRange,
    staleTime: 30_000,
  });

  const regenerateM = useMutation({
    mutationFn: () => api.regenerateTeamSummaryRange(start, end),
    onSuccess: (data) => {
      qc.setQueryData(["team-summary-range", start, end], data);
      qc.invalidateQueries({ queryKey: ["team-summaries-range"] });
    },
  });

  useEffect(() => {
    regenerateM.reset();
  }, [start, end]); // eslint-disable-line react-hooks/exhaustive-deps

  const generating = summaryQ.isFetching || regenerateM.isPending;
  const summary = summaryQ.data;
  const hasResults = Boolean(summary?.summary);
  const fromCache = summary?.from_cache;
  const days =
    start && end
      ? Math.max(
          1,
          Math.round(
            (new Date(end).getTime() - new Date(start).getTime()) / 86400000,
          ) + 1,
        )
      : 0;

  const sortedHistory = useMemo(() => {
    return (historyQ.data?.summaries ?? []).slice().sort((a, b) => {
      const da = a.generated_at ?? "";
      const db = b.generated_at ?? "";
      return db.localeCompare(da);
    });
  }, [historyQ.data]);

  return (
    <>
      <section className="card">
        <SectionHeader
          icon={<CalendarRange size={16} className="text-brand" />}
          title="期間を選んでトレンドサマリーを生成"
          subtitle="複数日の日報を横断し、繰り返しのパターン・離職リスク・対人摩擦などの兆候を AI が抽出します"
        />
        <div className="flex flex-wrap items-end gap-3 mt-2">
          <label className="grid gap-1">
            <span className="label">開始日</span>
            <input
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className="input-sm"
            />
          </label>
          <label className="grid gap-1">
            <span className="label">終了日</span>
            <input
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              className="input-sm"
            />
          </label>
          <button
            onClick={() => regenerateM.mutate()}
            disabled={generating || !start || !end}
            className="btn-secondary"
          >
            <RefreshCw size={14} className={regenerateM.isPending ? "animate-spin" : ""} />
            {regenerateM.isPending
              ? "AI 解析中…"
              : hasResults
                ? "再生成"
                : "AI で生成"}
          </button>
          {days > 0 && (
            <span className="text-xs text-slate-500">
              対象 {days} 日間 ({start} 〜 {end})
            </span>
          )}
          {fromCache && hasResults && !regenerateM.isPending && (
            <span className="pill-emerald" title={summary?.generated_at ?? undefined}>
              キャッシュから表示中
              {summary?.generated_at ? ` · ${formatJpDate(summary.generated_at)}` : ""}
            </span>
          )}
        </div>
        {regenerateM.isError && (
          <div className="mt-3">
            <InlineAlert tone="error">
              再生成に失敗しました: {(regenerateM.error as Error).message}
            </InlineAlert>
          </div>
        )}
      </section>

      <section className="grid gap-3">
        {summaryQ.isLoading && <SkeletonCard lines={5} />}
        {!summaryQ.isLoading && summaryQ.isError && (
          <InlineAlert tone="error">
            サマリーの取得に失敗しました: {(summaryQ.error as Error).message}
          </InlineAlert>
        )}
        {!summaryQ.isLoading && !hasResults && !regenerateM.isPending && (
          <EmptyState
            icon={<CalendarRange size={28} />}
            title="この期間のトレンドサマリーはまだ生成されていません"
            description="「AI で生成」を押すと Reporter エージェントが期間内の日報を読み込みます。"
          />
        )}
        {regenerateM.isPending && (
          <Spinner label="期間内の日報を横断して読み込んでいます…（10〜20秒）" />
        )}

        {hasResults && summary && <RangeResult summary={summary} />}
      </section>

      <section>
        <SectionHeader
          icon={<History size={16} className="text-brand" />}
          title="過去に生成した期間サマリー"
          subtitle="期間をクリックすると即座に表示します"
        />
        {historyQ.isLoading && <SkeletonCard lines={3} />}
        {!historyQ.isLoading && sortedHistory.length === 0 && (
          <EmptyState
            title="まだ生成履歴がありません"
            description="期間を指定して生成すると、ここに追加されます。"
          />
        )}
        {sortedHistory.length > 0 && (
          <ul className="grid gap-2">
            {sortedHistory.map((row) => {
              const active = row.start_date === start && row.end_date === end;
              return (
                <li key={row.key ?? `${row.start_date}_${row.end_date}`}>
                  <button
                    onClick={() => {
                      if (row.start_date) setStart(row.start_date);
                      if (row.end_date) setEnd(row.end_date);
                    }}
                    className={`w-full text-left card-tight transition flex items-center justify-between ${
                      active
                        ? "border-brand/40 bg-brand/5"
                        : "hover:border-brand/30 hover:bg-slate-50"
                    }`}
                  >
                    <span className="font-medium text-slate-800">
                      {row.start_date} 〜 {row.end_date}
                    </span>
                    <span className="text-xs text-slate-500 flex items-center gap-3">
                      {row.report_count != null && (
                        <span>{row.report_count} 件の日報</span>
                      )}
                      {row.member_count != null && (
                        <span>{row.member_count} 名</span>
                      )}
                      {row.generated_at && (
                        <span>{formatJpDate(row.generated_at)}</span>
                      )}
                      {active && <span className="pill-brand">表示中</span>}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </>
  );
}

function RangeResult({
  summary,
}: {
  summary: NonNullable<ReturnType<typeof api.teamSummaryRange> extends Promise<infer T> ? T : never>;
}) {
  const s = summary.summary;
  return (
    <>
      <p className="meta">
        {summary.report_count} 件の日報 / {summary.member_count} 名（
        {summary.start_date} 〜 {summary.end_date}）から作成
        {summary.generated_at && (
          <> ・ 生成 {formatJpDate(summary.generated_at)}</>
        )}
      </p>

      {s?.tldr && s.tldr.length > 0 && (
        <div className="card bg-gradient-to-br from-brand/5 to-transparent border-brand/20">
          <h3 className="section-title text-brand-dark mb-2">
            <Sparkles size={16} className="text-brand" /> 期間ハイライト
          </h3>
          <ul className="list-disc ml-5 text-sm grid gap-1">
            {s.tldr.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}

      {s?.risk_signals && s.risk_signals.length > 0 && (
        <div className="card border-rose-200 bg-rose-50/40">
          <h3 className="section-title text-rose-800 mb-3">
            <AlertTriangle size={16} className="text-rose-600" /> 注視すべきシグナル
          </h3>
          <ul className="grid gap-2.5">
            {s.risk_signals.map((r, i) => (
              <RiskSignalItem key={i} signal={r} />
            ))}
          </ul>
        </div>
      )}

      {s?.by_member && Object.keys(s.by_member).length > 0 && (
        <div className="card">
          <h3 className="section-title mb-3">
            <Users size={16} className="text-brand" /> メンバー別トレンド
          </h3>
          <ul className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(s.by_member).map(([name, trend]) => (
              <MemberTrendCard key={name} name={name} trend={trend} />
            ))}
          </ul>
        </div>
      )}

      {s?.themes && s.themes.length > 0 && (
        <div className="card">
          <h3 className="section-title mb-2">
            <Compass size={16} className="text-brand" /> 横断テーマ
          </h3>
          <ul className="list-disc ml-5 text-sm grid gap-1 text-slate-700">
            {s.themes.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}

      {s?.recommended_actions && s.recommended_actions.length > 0 && (
        <div className="card border-brand/20 bg-brand/5">
          <h3 className="section-title text-brand-dark mb-2">
            <Lightbulb size={16} className="text-brand" /> EM の次の一手
          </h3>
          <ul className="list-disc ml-5 text-sm grid gap-1 text-slate-700">
            {s.recommended_actions.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

function RiskSignalItem({ signal }: { signal: RangeRiskSignal }) {
  const meta = RISK_KIND_META[signal.kind ?? ""] ?? {
    label: signal.kind ?? "シグナル",
    emoji: "•",
    cls: "bg-slate-100 text-slate-700 border-slate-200",
  };
  return (
    <li className="rounded-lg border border-rose-200 bg-white p-3">
      <div className="flex flex-wrap items-baseline gap-2 mb-1">
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[11px] font-semibold ${meta.cls}`}
          title={signal.kind}
        >
          <span className="mr-1">{meta.emoji}</span>
          {meta.label}
        </span>
        {signal.member_name && (
          <span className="pill-rose">{signal.member_name}</span>
        )}
        {signal.evidence_dates && signal.evidence_dates.length > 0 && (
          <span className="text-[11px] text-slate-500">
            根拠日: {signal.evidence_dates.join(", ")}
          </span>
        )}
      </div>
      {signal.summary && (
        <p className="text-sm text-slate-800">{signal.summary}</p>
      )}
    </li>
  );
}

function MemberTrendCard({
  name,
  trend,
}: {
  name: string;
  trend: RangeMemberTrend;
}) {
  const meta = TREND_STYLES[trend.trend ?? ""] ?? TREND_STYLES["不変"];
  return (
    <li className="rounded-lg border border-slate-200 p-3 bg-white">
      <div className="flex items-baseline justify-between gap-2 mb-1">
        <span className="font-semibold text-slate-900 text-sm truncate">{name}</span>
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[11px] font-medium ${meta.cls}`}
        >
          {meta.icon}
          {meta.label}
        </span>
      </div>
      {trend.summary && (
        <p className="text-xs text-slate-700 leading-relaxed">{trend.summary}</p>
      )}
      {trend.evidence_dates && trend.evidence_dates.length > 0 && (
        <p className="text-[10px] text-slate-400 mt-1.5">
          {trend.evidence_dates.join(" · ")}
        </p>
      )}
    </li>
  );
}
