import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { meApi } from "@/lib/meApi";

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

  // 既存日報があれば編集モードでロード
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
        bullet_hints: hint.split("\n").map((s) => s.trim()).filter(Boolean),
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
    <div className="grid gap-4 sm:gap-6 lg:grid-cols-3">
      <section className="lg:col-span-2">
        <h1 className="text-xl sm:text-2xl font-bold mb-3">日報</h1>
        <div className="card">
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-3">
            <label className="text-sm text-slate-600">日付:</label>
            <input
              type="date"
              value={reportDate}
              onChange={(e) => setReportDate(e.target.value)}
              className="border border-slate-300 rounded px-2 py-1 text-sm"
            />
          </div>

          <div className="mb-3">
            <label className="text-xs text-slate-500">AI に下書きを書かせるヒント（任意・改行で複数）</label>
            <textarea
              value={hint}
              onChange={(e) => setHint(e.target.value)}
              placeholder={`例:\nメンターと決済 API のペアプロをした\nテスト失敗の原因を調べた`}
              className="w-full h-20 border border-slate-300 rounded p-2 text-sm mt-1"
            />
            <button
              onClick={() => draftM.mutate()}
              disabled={draftM.isPending}
              className="btn-ghost mt-2"
            >
              {draftM.isPending ? "AI が考え中…" : "AI に下書きさせる"}
            </button>
          </div>

          <Section title="昨日">
            <textarea
              value={yesterday}
              onChange={(e) => setYesterday(e.target.value)}
              className="w-full h-20 border border-slate-300 rounded p-2 text-sm"
            />
          </Section>
          <Section title="今日">
            <textarea
              value={todayText}
              onChange={(e) => setTodayText(e.target.value)}
              className="w-full h-20 border border-slate-300 rounded p-2 text-sm"
            />
          </Section>
          <Section title="ブロッカー">
            <textarea
              value={blockers}
              onChange={(e) => setBlockers(e.target.value)}
              className="w-full h-16 border border-slate-300 rounded p-2 text-sm"
            />
          </Section>

          <div className="mt-3 flex items-center gap-3">
            <button
              onClick={() => saveM.mutate()}
              disabled={saveM.isPending}
              className="btn-primary"
            >
              {saveM.isPending ? "保存中…" : "保存"}
            </button>
            {statusMsg && <span className="text-sm text-emerald-700">{statusMsg}</span>}
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-2">これまでの日報</h2>
        <div className="grid gap-2">
          {(dailyQ.data?.reports ?? []).slice().reverse().slice(0, 14).map((r) => (
            <button
              key={r.id}
              onClick={() => setReportDate(r.report_date)}
              className={`card text-left hover:shadow-md transition ${
                r.report_date === reportDate ? "ring-2 ring-brand" : ""
              }`}
            >
              <div className="flex items-baseline justify-between">
                <span className="font-medium text-sm">{r.report_date}</span>
                {r.blockers && <span className="pill bg-rose-100 text-rose-700">ブロッカー</span>}
              </div>
              <p className="text-xs text-slate-500 mt-1 line-clamp-2">{r.today}</p>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-2">
      <label className="text-xs text-slate-500">{title}</label>
      <div className="mt-1">{children}</div>
    </div>
  );
}
