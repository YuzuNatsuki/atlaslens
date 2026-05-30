import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarCheck, NotebookPen, Save } from "lucide-react";

import { meApi } from "@/lib/meApi";
import {
  EmptyState,
  InlineAlert,
  PageHeader,
  SectionHeader,
  SkeletonCard,
} from "@/components/ui";

export default function MyOneOnOnes() {
  const qc = useQueryClient();
  const historyQ = useQuery({ queryKey: ["me", "1on1s"], queryFn: meApi.oneOnOnes });
  const prepQ = useQuery({ queryKey: ["me", "prep"], queryFn: meApi.getPrepNotes });

  const [notes, setNotes] = useState("");
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    if (prepQ.data) setNotes(prepQ.data.notes ?? "");
  }, [prepQ.data?.notes]); // eslint-disable-line react-hooks/exhaustive-deps

  const saveM = useMutation({
    mutationFn: () => meApi.savePrepNotes(notes),
    onSuccess: () => {
      setStatusMsg("保存しました。次回の 1on1 で EM が参照できます。");
      qc.invalidateQueries({ queryKey: ["me", "prep"] });
    },
  });

  return (
    <div className="grid gap-6">
      <PageHeader
        title="マイ 1on1"
        subtitle="次回 1on1 の準備メモと、過去の 1on1 履歴を確認できます。"
      />

      <section className="card">
        <SectionHeader
          icon={<NotebookPen size={16} className="text-brand" />}
          title="次回 1on1 で話したいこと"
          subtitle="このメモは EM の面談前の資料に反映されます。いつでも更新できます。"
        />
        <textarea
          value={notes}
          onChange={(e) => {
            setNotes(e.target.value);
            setStatusMsg(null);
          }}
          placeholder={
            "例:\n- 評価のフィードバック\n- 来期のチャレンジ案\n- 設計レビューに参加したい"
          }
          className="textarea"
          style={{ minHeight: 140 }}
        />
        <div className="flex items-center gap-3 mt-2 flex-wrap">
          <button
            onClick={() => saveM.mutate()}
            disabled={saveM.isPending}
            className="btn-primary"
          >
            <Save size={14} />
            {saveM.isPending ? "保存中…" : "保存"}
          </button>
          {prepQ.data?.updated_at && (
            <span className="meta">最終更新: {prepQ.data.updated_at}</span>
          )}
          {statusMsg && <InlineAlert tone="success">{statusMsg}</InlineAlert>}
        </div>
      </section>

      <section>
        <SectionHeader
          icon={<CalendarCheck size={16} className="text-brand" />}
          title="1on1 履歴"
        />
        {historyQ.isLoading && <SkeletonCard lines={3} />}
        {historyQ.data && historyQ.data.one_on_ones.length === 0 && (
          <EmptyState
            title="まだ 1on1 の記録がありません"
            description="EM が記録すると、ここに表示されます。"
          />
        )}
        <div className="grid gap-3">
          {(historyQ.data?.one_on_ones ?? [])
            .slice()
            .reverse()
            .map((o) => (
              <article key={o.id} className="card">
                <header className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1 mb-2">
                  <span className="font-medium">
                    {new Date(o.held_at).toLocaleString("ja-JP")}
                  </span>
                  <span className="meta truncate">{o.topics.join(" · ")}</span>
                </header>
                <p className="text-sm whitespace-pre-wrap">{o.notes}</p>
                {o.todos.length > 0 && (
                  <div className="mt-3">
                    <p className="eyebrow mb-1">ToDo</p>
                    <ul className="text-sm list-disc ml-5 grid gap-0.5">
                      {o.todos.map((t, i) => (
                        <li key={i}>{t}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {o.follow_ups.length > 0 && (
                  <div className="mt-3">
                    <p className="eyebrow mb-1">フォローアップ</p>
                    <ul className="text-sm list-disc ml-5 grid gap-0.5">
                      {o.follow_ups.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </article>
            ))}
        </div>
      </section>
    </div>
  );
}
