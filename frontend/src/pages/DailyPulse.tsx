import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/lib/api";
import { pickText } from "@/lib/format";

export default function DailyPulsePage() {
  const [reportDate, setReportDate] = useState("2026-05-12");
  const summaryQ = useQuery({
    queryKey: ["team-summary", reportDate],
    queryFn: () => api.teamSummary(reportDate),
    enabled: false,  // Don't auto-fire — trigger via button below.
  });

  return (
    <div className="grid gap-6">
      <section className="card">
        <h2 className="text-lg font-semibold mb-2">日報サマリー — チーム要約</h2>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <label className="text-sm text-slate-600">日付:</label>
          <input
            type="date"
            value={reportDate}
            onChange={(e) => setReportDate(e.target.value)}
            className="border border-slate-300 rounded px-2 py-1 text-sm"
          />
          <button
            onClick={() => summaryQ.refetch()}
            disabled={summaryQ.isFetching}
            className="btn-primary"
          >
            {summaryQ.isFetching
              ? "AI 要約中… (~5s)"
              : summaryQ.data
                ? "再生成"
                : "要約を生成"}
          </button>
        </div>
        {!summaryQ.data && !summaryQ.isFetching && (
          <p className="text-sm text-slate-500 mt-2">
            日付を選んでボタンを押すと、Reporter エージェントが当日のメンバー全員の日報を読み込み、
            5 秒前後でチーム全体のトピックや気がかりな点を整理してお返しします。
          </p>
        )}
      </section>

      {summaryQ.isFetching && <p className="text-slate-500">AI が要約中…</p>}
      {summaryQ.data && (
        <div className="grid gap-3">
          <div className="text-xs text-slate-400 flex items-center gap-1">
            📎 参照データ: {summaryQ.data.report_count} 件の日報（{reportDate}）を Reporter エージェントが読み込みました
          </div>
          {summaryQ.data.summary.tldr && (
            <div className="card">
              <h3 className="font-medium text-sm text-brand mb-2">TL;DR</h3>
              <ul className="list-disc ml-5 text-sm">
                {summaryQ.data.summary.tldr.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </div>
          )}

          {summaryQ.data.summary.highlights && (
            <div className="card">
              <h3 className="font-medium text-sm text-brand mb-2">メンバーハイライト</h3>
              <ul className="list-disc ml-5 text-sm">
                {Object.entries(summaryQ.data.summary.highlights).map(([k, v]) => (
                  <li key={k}>
                    <strong>{k}</strong>: {pickText(v)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {summaryQ.data.summary.blockers_to_surface && (
            <div className="card">
              <h3 className="font-medium text-sm text-rose-700 mb-2">サーフェスすべきブロッカー</h3>
              <ul className="list-disc ml-5 text-sm">
                {Object.entries(summaryQ.data.summary.blockers_to_surface).map(([k, v]) => (
                  <li key={k}>
                    <strong>{k}</strong>: {pickText(v)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {summaryQ.data.summary.themes && (
            <div className="card">
              <h3 className="font-medium text-sm text-slate-600 mb-2">横断テーマ</h3>
              <ul className="list-disc ml-5 text-sm">
                {summaryQ.data.summary.themes.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
