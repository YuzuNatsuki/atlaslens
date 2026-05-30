import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CalendarDays,
  Compass,
  History,
  RefreshCw,
  Sparkles,
  Users,
} from "lucide-react";

import { api, type PastTeamSummary } from "@/lib/api";
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

export default function DailyPulsePage() {
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
    <div className="grid gap-8">
      <PageHeader
        title="日報サマリー"
        subtitle="AI がチーム全員の日報を読み、朝会前 30 秒で把握できる形に要約します。一度生成すれば次回以降はすぐ再表示できます。"
      />

      <section className="card">
        <SectionHeader
          icon={<CalendarDays size={16} className="text-brand" />}
          title="日付を選んでサマリーを表示"
          subtitle="初回は 5〜10 秒かかります。一度作った要約はすぐ再表示できます"
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
              保存済みの要約
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
            description="「AI で生成」を押すと、日報を読み込んで要約を作ります。"
          />
        )}
        {regenerateM.isPending && <Spinner label="AI が日報を読み込んでいます…" />}

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
          subtitle="日付をクリックすると、保存済みの要約をすぐ表示します"
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
    </div>
  );
}
