import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, Save, Sparkles } from "lucide-react";

import { meApi } from "@/lib/meApi";
import {
  EmptyState,
  InlineAlert,
  PageHeader,
  SectionHeader,
} from "@/components/ui";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function MyDaily() {
  const qc = useQueryClient();
  const dailyQ = useQuery({ queryKey: ["me", "daily"], queryFn: meApi.dailyReports });

  const [reportDate, setReportDate] = useState<string>(today());
  const [yesterday, setYesterday] = useState("");
  const [todayText, setTodayText] = useState("");
  const [blockers, setBlockers] = useState("");
  const [hint, setHint] = useState("");
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    const existing = dailyQ.data?.reports.find((r) => r.report_date === reportDate);
    if (existing) {
      setYesterday(existing.yesterday);
      setTodayText(existing.today);
      setBlockers(existing.blockers);
    } else {
      setYesterday("");
      setTodayText("");
      setBlockers("");
    }
    setStatusMsg(null);
  }, [reportDate, dailyQ.data]);

  const draftM = useMutation({
    mutationFn: () =>
      meApi.draftDailyReport({
        report_date: reportDate,
        bullet_hints: hint
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
      }),
    onSuccess: (resp) => {
      const d = resp.draft;
      if (d.yesterday) setYesterday(d.yesterday);
      if (d.today) setTodayText(d.today);
      if (d.blockers) setBlockers(d.blockers);
      setStatusMsg("AI ドラフトを反映しました。確認して保存してください。");
    },
  });

  const saveM = useMutation({
    mutationFn: () =>
      meApi.submitDailyReport({
        report_date: reportDate,
        yesterday,
        today: todayText,
        blockers,
        mood: null,
      }),
    onSuccess: () => {
      setStatusMsg("保存しました。");
      qc.invalidateQueries({ queryKey: ["me", "daily"] });
    },
  });

  return (
    <div className="grid gap-6">
      <PageHeader
        title="日報"
        subtitle="毎日の進捗を記録します。AI ドラフト機能で 30 秒で書き始められます。"
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2 grid gap-3">
          <div className="card">
            <div className="flex flex-wrap items-end gap-3 mb-3">
              <label className="grid gap-1">
                <span className="label">日付</span>
                <input
                  type="date"
                  value={reportDate}
                  onChange={(e) => setReportDate(e.target.value)}
                  className="input-sm"
                />
              </label>
            </div>

            <div className="mb-3">
              <label className="label">
                AI に下書きを書かせるヒント（任意・改行で複数）
              </label>
              <textarea
                value={hint}
                onChange={(e) => setHint(e.target.value)}
                placeholder={`例:\nメンターと決済 API のペアプロをした\nテスト失敗の原因を調べた`}
                className="textarea"
                style={{ minHeight: 80 }}
              />
              <button
                onClick={() => draftM.mutate()}
                disabled={draftM.isPending}
                className="btn-secondary mt-2"
              >
                <Sparkles size={14} />
                {draftM.isPending ? "AI が考え中…" : "AI に下書きさせる"}
              </button>
            </div>

            <Section title="昨日">
              <textarea
                value={yesterday}
                onChange={(e) => setYesterday(e.target.value)}
                className="textarea"
                style={{ minHeight: 80 }}
              />
            </Section>
            <Section title="今日">
              <textarea
                value={todayText}
                onChange={(e) => setTodayText(e.target.value)}
                className="textarea"
                style={{ minHeight: 80 }}
              />
            </Section>
            <Section title="ブロッカー">
              <textarea
                value={blockers}
                onChange={(e) => setBlockers(e.target.value)}
                className="textarea"
                style={{ minHeight: 60 }}
              />
            </Section>

            <div className="mt-3 flex items-center gap-3 flex-wrap">
              <button
                onClick={() => saveM.mutate()}
                disabled={saveM.isPending}
                className="btn-primary"
              >
                <Save size={14} />
                {saveM.isPending ? "保存中…" : "保存"}
              </button>
              {statusMsg && <InlineAlert tone="success">{statusMsg}</InlineAlert>}
              {saveM.isError && (
                <InlineAlert tone="error">
                  保存に失敗しました: {(saveM.error as Error).message}
                </InlineAlert>
              )}
            </div>
          </div>
        </section>

        <section>
          <SectionHeader
            icon={<CalendarDays size={16} className="text-brand" />}
            title="これまでの日報"
          />
          {dailyQ.data?.reports.length === 0 && (
            <EmptyState
              title="日報がまだありません"
              description="左のフォームから最初の 1 件を保存してください。"
            />
          )}
          <div className="grid gap-2">
            {(dailyQ.data?.reports ?? [])
              .slice()
              .reverse()
              .slice(0, 14)
              .map((r) => (
                <button
                  key={r.id}
                  onClick={() => setReportDate(r.report_date)}
                  className={`card-tight text-left transition hover:border-brand/30 ${
                    r.report_date === reportDate
                      ? "ring-2 ring-brand/40 border-brand/40"
                      : ""
                  }`}
                >
                  <div className="flex items-baseline justify-between">
                    <span className="font-medium text-sm">{r.report_date}</span>
                    {r.blockers && (
                      <span className="pill-rose">ブロッカー</span>
                    )}
                  </div>
                  <p className="meta mt-1 line-clamp-2">{r.today}</p>
                </button>
              ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-2.5">
      <label className="label">{title}</label>
      {children}
    </div>
  );
}
