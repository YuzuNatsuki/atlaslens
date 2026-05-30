import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarDays,
  CloudOff,
  RotateCcw,
  Save,
  Sparkles,
  Trash2,
} from "lucide-react";

import { meApi } from "@/lib/meApi";
import { useCurrentUser } from "@/lib/auth";
import {
  dailyDraftKey,
  isDailyDraftDirty,
  type DailyDraft,
} from "@/lib/dailyDraft";
import { deleteDraft, getDraft, setDraft } from "@/lib/draftStore";
import {
  EmptyState,
  InlineAlert,
  PageHeader,
  SectionHeader,
} from "@/components/ui";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

type DraftStatus = "idle" | "saving" | "saved" | "restored";

function formatHm(d: Date | null): string {
  if (!d) return "";
  return d.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
}

export default function MyDaily() {
  const qc = useQueryClient();
  const userQ = useCurrentUser();
  const memberId = userQ.data?.member_id ?? null;

  const dailyQ = useQuery({ queryKey: ["me", "daily"], queryFn: meApi.dailyReports });

  const [reportDate, setReportDate] = useState<string>(today());
  const [yesterday, setYesterday] = useState("");
  const [todayText, setTodayText] = useState("");
  const [blockers, setBlockers] = useState("");
  const [hint, setHint] = useState("");
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // Draft (IndexedDB) state — separate from the form fields above.
  const [draftStatus, setDraftStatus] = useState<DraftStatus>("idle");
  const [draftSavedAt, setDraftSavedAt] = useState<Date | null>(null);
  const baselineRef = useRef({ yesterday: "", today: "", blockers: "" });
  // We block the autosave for one tick after programmatic loads (server data
  // → form, draft → form, AI draft → form) so the loaded data itself doesn't
  // immediately get re-written to IDB. Each load increments the generation;
  // the autosave effect compares the generation it saw at debounce-end with
  // the current one to decide whether to write.
  const loadGenRef = useRef(0);

  // -------- server → form (and overlay any locally-saved draft) --------
  useEffect(() => {
    if (!memberId || !reportDate) return;
    let cancelled = false;
    loadGenRef.current += 1;

    (async () => {
      const existing = dailyQ.data?.reports.find(
        (r) => r.report_date === reportDate,
      );
      const baseY = existing?.yesterday ?? "";
      const baseT = existing?.today ?? "";
      const baseB = existing?.blockers ?? "";
      baselineRef.current = { yesterday: baseY, today: baseT, blockers: baseB };

      const key = dailyDraftKey(memberId, reportDate);
      const draft = await getDraft<DailyDraft>(key);
      if (cancelled) return;

      const dirty =
        draft &&
        isDailyDraftDirty(
          {
            yesterday: draft.yesterday,
            today: draft.today,
            blockers: draft.blockers,
            hint: draft.hint ?? "",
          },
          { yesterday: baseY, today: baseT, blockers: baseB },
        );

      if (draft && dirty) {
        setYesterday(draft.yesterday);
        setTodayText(draft.today);
        setBlockers(draft.blockers);
        setHint(draft.hint ?? "");
        setDraftStatus("restored");
        setDraftSavedAt(draft.updated_at ? new Date(draft.updated_at) : null);
      } else {
        setYesterday(baseY);
        setTodayText(baseT);
        setBlockers(baseB);
        setHint("");
        setDraftStatus("idle");
        setDraftSavedAt(null);
        if (draft) {
          // Stale draft that matches server — clean up so the indicator
          // stops claiming there's an unsaved version.
          await deleteDraft(key);
        }
      }
      setStatusMsg(null);
    })();

    return () => {
      cancelled = true;
    };
  }, [memberId, reportDate, dailyQ.data]);

  // -------- form → IDB (debounced autosave) --------
  useEffect(() => {
    if (!memberId || !reportDate) return;
    const generationAtScheduleTime = loadGenRef.current;
    const baseline = baselineRef.current;
    const dirty = isDailyDraftDirty(
      { yesterday, today: todayText, blockers, hint },
      baseline,
    );
    const key = dailyDraftKey(memberId, reportDate);

    if (!dirty) {
      // Form matches server again (e.g. user reverted, or just saved).
      void deleteDraft(key);
      setDraftStatus((s) => (s === "restored" ? s : "idle"));
      return;
    }

    setDraftStatus("saving");
    const handle = window.setTimeout(async () => {
      // If the user navigated to another date / reloaded fresh server data
      // while we were waiting, skip the write so we don't clobber the new
      // load with the previous date's content.
      if (loadGenRef.current !== generationAtScheduleTime) return;
      const updatedAt = new Date().toISOString();
      await setDraft<DailyDraft>(key, {
        yesterday,
        today: todayText,
        blockers,
        hint,
        updated_at: updatedAt,
      });
      setDraftSavedAt(new Date(updatedAt));
      setDraftStatus("saved");
    }, 600);

    return () => window.clearTimeout(handle);
  }, [memberId, reportDate, yesterday, todayText, blockers, hint]);

  // -------- mutations --------

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
      // Bump generation so the autosave doesn't immediately re-write what
      // the AI just put in. (User edits will trigger it again normally.)
      loadGenRef.current += 1;
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
    onSuccess: async () => {
      if (memberId) {
        await deleteDraft(dailyDraftKey(memberId, reportDate));
      }
      setDraftStatus("idle");
      setDraftSavedAt(null);
      setStatusMsg("保存しました。");
      qc.invalidateQueries({ queryKey: ["me", "daily"] });
    },
  });

  // -------- helpers wired to the restore banner --------

  const revertToServer = useCallback(async () => {
    if (!memberId || !reportDate) return;
    loadGenRef.current += 1;
    const { yesterday: y, today: t, blockers: b } = baselineRef.current;
    setYesterday(y);
    setTodayText(t);
    setBlockers(b);
    setHint("");
    await deleteDraft(dailyDraftKey(memberId, reportDate));
    setDraftStatus("idle");
    setDraftSavedAt(null);
  }, [memberId, reportDate]);

  const dismissDraft = useCallback(async () => {
    if (!memberId || !reportDate) return;
    await deleteDraft(dailyDraftKey(memberId, reportDate));
    setDraftStatus("idle");
  }, [memberId, reportDate]);

  // -------- derived view state --------

  const restoreVisible = draftStatus === "restored";

  const statusPill = useMemo(() => {
    switch (draftStatus) {
      case "saving":
        return (
          <span className="inline-flex items-center gap-1 text-xs text-slate-500">
            <CloudOff size={12} /> 下書きを端末に保存中…
          </span>
        );
      case "saved":
        return (
          <span className="inline-flex items-center gap-1 text-xs text-emerald-700">
            <CloudOff size={12} />
            この端末に下書きを保存しました ({formatHm(draftSavedAt)})
          </span>
        );
      case "restored":
        return (
          <span className="inline-flex items-center gap-1 text-xs text-brand-dark">
            <RotateCcw size={12} />
            未保存の下書きを復元
            {draftSavedAt ? `（${formatHm(draftSavedAt)} 時点）` : ""}
          </span>
        );
      default:
        return null;
    }
  }, [draftStatus, draftSavedAt]);

  return (
    <div className="grid gap-6">
      <PageHeader
        title="日報"
        subtitle="毎日の進捗を記録します。AI ドラフト機能で 30 秒で書き始められます。書きかけはこの端末のブラウザに自動保存され、タブを閉じても復元されます。"
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
              <div className="ml-auto">{statusPill}</div>
            </div>

            {restoreVisible && (
              <div className="mb-3 rounded-lg border border-brand/20 bg-brand/5 px-3 py-2 text-xs text-slate-700 flex flex-wrap items-center gap-2">
                <RotateCcw size={14} className="text-brand" />
                <span className="font-medium text-brand-dark">
                  この端末に保存された未送信の下書きを復元しました。
                </span>
                <span className="text-slate-500">
                  そのまま続きを書いて「保存」してください。
                </span>
                <span className="ml-auto flex gap-2">
                  <button
                    type="button"
                    onClick={revertToServer}
                    className="text-xs underline text-slate-600 hover:text-slate-900 inline-flex items-center gap-1"
                  >
                    <RotateCcw size={12} /> サーバの保存版に戻す
                  </button>
                  <button
                    type="button"
                    onClick={dismissDraft}
                    className="text-xs underline text-slate-500 hover:text-rose-700 inline-flex items-center gap-1"
                    title="復元バナーを閉じる（下書き自体は保持されます）"
                  >
                    <Trash2 size={12} /> バナーを閉じる
                  </button>
                </span>
              </div>
            )}

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
            <Section title="進められないこと">
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
                      <span className="pill-rose">課題あり</span>
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
