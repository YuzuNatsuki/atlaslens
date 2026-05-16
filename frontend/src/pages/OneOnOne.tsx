import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Save } from "lucide-react";

import { api } from "@/lib/api";
import { pickText } from "@/lib/format";

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function OneOnOnePage() {
  const { memberId = "" } = useParams<{ memberId: string }>();
  const qc = useQueryClient();
  const [rawNotes, setRawNotes] = useState("");
  const [heldOn, setHeldOn] = useState(todayISO());
  const [topics, setTopics] = useState("");
  const [todos, setTodos] = useState("");
  const [followUps, setFollowUps] = useState("");
  const [structuredNotes, setStructuredNotes] = useState("");
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const packetQ = useQuery({
    queryKey: ["1on1-packet", memberId],
    queryFn: () => api.getOneOnOnePacket(memberId),
    enabled: Boolean(memberId),
  });

  const draftM = useMutation({
    mutationFn: () => api.draftMinutes({ member_id: memberId, raw_notes: rawNotes }),
  });

  // 整形結果が来たら保存フォームの初期値に反映
  useEffect(() => {
    const s = draftM.data?.structured;
    if (!s) return;
    setStructuredNotes(s.summary ?? rawNotes);
    setTopics((s.key_topics ?? []).join("\n"));
    setTodos(
      (s.todos ?? [])
        .map((t) => {
          const owner = t.owner ? `${t.owner}: ` : "";
          const due = t.due ? ` (〜${t.due})` : "";
          return `${owner}${t.task}${due}`;
        })
        .join("\n"),
    );
    setFollowUps((s.follow_ups_for_next_time ?? []).join("\n"));
  }, [draftM.data]);

  const saveM = useMutation({
    mutationFn: () =>
      api.saveOneOnOneRecord({
        member_id: memberId,
        held_on: heldOn,
        topics: topics.split("\n").map((s) => s.trim()).filter(Boolean),
        notes: structuredNotes.trim() || rawNotes.trim(),
        todos: todos.split("\n").map((s) => s.trim()).filter(Boolean),
        follow_ups: followUps.split("\n").map((s) => s.trim()).filter(Boolean),
      }),
    onSuccess: () => {
      setSaveMsg("1on1 を記録として保存しました。Member 側でも閲覧できます。");
      qc.invalidateQueries({ queryKey: ["1on1-packet", memberId] });
    },
  });

  return (
    <div className="grid gap-4 lg:gap-6 lg:grid-cols-2">
      <section>
        <h2 className="text-lg font-semibold mb-3">事前パケット</h2>
        {packetQ.isLoading && (
          <p className="text-slate-500">準備中… (AI が直近の活動を確認しています)</p>
        )}
        {packetQ.data && (
          <div className="grid gap-3">
            {packetQ.data.packet.opening_check_in && (
              <div className="card">
                <h3 className="font-medium text-sm text-brand mb-1">オープニング</h3>
                <p className="text-sm">{packetQ.data.packet.opening_check_in}</p>
              </div>
            )}
            <SectionBlock
              title="議論ポイント候補"
              items={(packetQ.data.packet.discussion_topics ?? []).map((t: any) => ({
                primary: pickText(t),
                secondary: Array.isArray(t?.evidence) ? t.evidence.join(", ") : undefined,
              }))}
            />
            <SectionBlock
              title="成長を引き出す質問"
              items={(packetQ.data.packet.growth_questions ?? []).map((q: any) => ({
                primary: pickText(q),
              }))}
            />
            <SectionBlock
              title="サーフェスすべきブロッカー"
              items={(packetQ.data.packet.blockers_to_surface ?? []).map((b: any) => ({
                primary: pickText(b),
              }))}
              tone="text-rose-700"
            />
            <SectionBlock
              title="前回からのフォローアップ"
              items={(packetQ.data.packet.follow_ups_from_last_time ?? []).map((f: any) => ({
                primary: pickText(f),
              }))}
            />
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">議事録ドラフト + 記録保存</h2>
        <div className="card">
          <label className="text-xs text-slate-500">1on1 中のメモ（生）</label>
          <textarea
            value={rawNotes}
            onChange={(e) => setRawNotes(e.target.value)}
            placeholder="話したことをそのままメモ。後で AI が整形します。"
            className="w-full h-32 border border-slate-300 rounded p-2 text-sm mt-1"
          />
          <button
            onClick={() => draftM.mutate()}
            disabled={!rawNotes || draftM.isPending}
            className="btn-primary mt-2"
          >
            {draftM.isPending ? "整形中..." : "議事録に整形 + ToDo を抽出"}
          </button>
        </div>

        <div className="card mt-3">
          <h3 className="font-medium text-sm text-brand mb-2">記録として保存</h3>

          <div className="grid sm:grid-cols-2 gap-3 mb-3">
            <label className="grid gap-1">
              <span className="text-xs text-slate-500">日付</span>
              <input
                type="date"
                value={heldOn}
                onChange={(e) => setHeldOn(e.target.value)}
                className="border border-slate-300 rounded px-2 py-1.5"
              />
            </label>
          </div>

          <Field label="議題 (1行1件)">
            <textarea
              value={topics}
              onChange={(e) => setTopics(e.target.value)}
              className="w-full h-16 border border-slate-300 rounded p-2 text-sm"
            />
          </Field>
          <Field label="ノート">
            <textarea
              value={structuredNotes}
              onChange={(e) => setStructuredNotes(e.target.value)}
              className="w-full h-24 border border-slate-300 rounded p-2 text-sm"
            />
          </Field>
          <Field label="ToDo (1行1件)">
            <textarea
              value={todos}
              onChange={(e) => setTodos(e.target.value)}
              className="w-full h-20 border border-slate-300 rounded p-2 text-sm"
            />
          </Field>
          <Field label="フォローアップ (1行1件)">
            <textarea
              value={followUps}
              onChange={(e) => setFollowUps(e.target.value)}
              className="w-full h-16 border border-slate-300 rounded p-2 text-sm"
            />
          </Field>

          <div className="flex items-center gap-2 mt-2">
            <button
              onClick={() => saveM.mutate()}
              disabled={saveM.isPending || (!structuredNotes.trim() && !rawNotes.trim())}
              className="btn-primary flex items-center gap-1"
            >
              <Save size={14} />
              {saveM.isPending ? "保存中…" : "1on1 を保存"}
            </button>
            {saveMsg && <span className="text-sm text-emerald-700">{saveMsg}</span>}
          </div>
        </div>
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-2">
      <label className="text-xs text-slate-500">{label}</label>
      <div className="mt-1">{children}</div>
    </div>
  );
}

function SectionBlock({
  title,
  items,
  tone,
}: {
  title: string;
  items?: Array<{ primary: string; secondary?: string }>;
  tone?: string;
}) {
  if (!items || items.length === 0) return null;
  return (
    <div className="card">
      <h3 className={`font-medium text-sm mb-1 ${tone ?? "text-slate-700"}`}>{title}</h3>
      <ul className="text-sm list-disc ml-5">
        {items.map((it, i) => (
          <li key={i}>
            {it.primary}
            {it.secondary && (
              <span className="text-xs text-slate-400 ml-1">({it.secondary})</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
