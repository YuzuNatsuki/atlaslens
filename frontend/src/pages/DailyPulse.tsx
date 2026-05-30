import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { CalendarDays, History, RefreshCw } from "lucide-react";

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

const DEFAULT_DATE = "2026-05-12";

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
        subtitle="Reporter エージェントがチーム全員の日報を読み込み、チームの注目点を整理します。生成済みのサマリーは Cosmos DB に保存され、次回以降は即座に再利用されます。"
      />

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
              📎 参照データ: {summary?.report_count ?? 0} 件の日報（{reportDate}）·{" "}
              {summary?.generated_at && (
                <>生成日時 {formatJpDate(summary.generated_at)}</>
              )}
            </p>

            {summary?.summary?.tldr && (
              <div className="card">
                <h3 className="font-medium text-sm text-brand-dark mb-2">TL;DR</h3>
                <ul className="list-disc ml-5 text-sm grid gap-1">
                  {summary.summary.tldr.map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ul>
              </div>
            )}

            {summary?.summary?.highlights && (
              <div className="card">
                <h3 className="font-medium text-sm text-brand-dark mb-2">メンバーハイライト</h3>
                <ul className="list-disc ml-5 text-sm grid gap-1">
                  {Object.entries(summary.summary.highlights).map(([k, v]) => (
                    <li key={k}>
                      <strong>{k}</strong>: {pickText(v)}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {summary?.summary?.blockers_to_surface && (
              <div className="card border-rose-200">
                <h3 className="font-medium text-sm text-rose-700 mb-2">
                  サーフェスすべきブロッカー
                </h3>
                <ul className="list-disc ml-5 text-sm grid gap-1">
                  {Object.entries(summary.summary.blockers_to_surface).map(([k, v]) => (
                    <li key={k}>
                      <strong>{k}</strong>: {pickText(v)}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {summary?.summary?.themes && summary.summary.themes.length > 0 && (
              <div className="card">
                <h3 className="font-medium text-sm text-slate-600 mb-2">横断テーマ</h3>
                <ul className="list-disc ml-5 text-sm grid gap-1">
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
    </div>
  );
}
