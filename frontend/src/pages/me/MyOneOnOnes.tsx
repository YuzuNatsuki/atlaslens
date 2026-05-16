import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save } from "lucide-react";

import { meApi } from "@/lib/meApi";

export default function MyOneOnOnes() {
  const qc = useQueryClient();
  const historyQ = useQuery({ queryKey: ["me", "1on1s"], queryFn: meApi.oneOnOnes });
  const prepQ = useQuery({ queryKey: ["me", "prep"], queryFn: meApi.getPrepNotes });

  const [notes, setNotes] = useState("");
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    if (prepQ.data) setNotes(prepQ.data.notes ?? "");
  }, [prepQ.data?.notes]);

  const saveM = useMutation({
    mutationFn: () => meApi.savePrepNotes(notes),
    onSuccess: () => {
      setStatusMsg("保存しました。次回の 1on1 で EM が参照できます。");
      qc.invalidateQueries({ queryKey: ["me", "prep"] });
    },
  });

  return (
    <div className="grid gap-4 sm:gap-6">
      <h1 className="text-xl sm:text-2xl font-bold">マイ 1on1</h1>

      <section className="card">
        <h2 className="font-semibold mb-1">次回 1on1 で話したいこと</h2>
        <p className="text-xs text-slate-500 mb-3">
          このメモは EM の 1on1 事前パケットに反映されます。いつでも更新できます。
        </p>
        <textarea
          value={notes}
          onChange={(e) => {
            setNotes(e.target.value);
            setStatusMsg(null);
          }}
          placeholder={"例:\n- 評価のフィードバック\n- 来期のチャレンジ案\n- 設計レビューに参加したい"}
          className="w-full h-32 border border-slate-300 rounded p-2 text-sm"
        />
        <div className="flex items-center gap-3 mt-2">
          <button
            onClick={() => saveM.mutate()}
            disabled={saveM.isPending}
            className="btn-primary flex items-center gap-1"
          >
            <Save size={14} />
            {saveM.isPending ? "保存中…" : "保存"}
          </button>
          {prepQ.data?.updated_at && (
            <span className="text-xs text-slate-500">最終更新: {prepQ.data.updated_at}</span>
          )}
          {statusMsg && <span className="text-sm text-emerald-700">{statusMsg}</span>}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-2">1on1 履歴</h2>
        {historyQ.isLoading && <p className="text-slate-500">読み込み中…</p>}
        {historyQ.data && historyQ.data.one_on_ones.length === 0 && (
          <p className="text-slate-500">まだ 1on1 の記録がありません。</p>
        )}
        <div className="grid gap-3">
          {(historyQ.data?.one_on_ones ?? [])
            .slice()
            .reverse()
            .map((o) => (
              <article key={o.id} className="card">
                <header className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1 mb-2">
                  <span className="font-medium">{new Date(o.held_at).toLocaleString()}</span>
                  <span className="text-xs text-slate-500">{o.topics.join(" · ")}</span>
                </header>
                <p className="text-sm whitespace-pre-wrap">{o.notes}</p>
                {o.todos.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs text-slate-500 mb-1">ToDo</p>
                    <ul className="text-sm list-disc ml-5">
                      {o.todos.map((t, i) => (
                        <li key={i}>{t}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {o.follow_ups.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs text-slate-500 mb-1">フォローアップ</p>
                    <ul className="text-sm list-disc ml-5">
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
