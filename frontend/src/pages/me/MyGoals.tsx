import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Save, Trash2, X } from "lucide-react";

import { meApi, type MyGoal, type GoalPayload } from "@/lib/meApi";

const STATUS_OPTIONS: { value: string; label: string; tone: string }[] = [
  { value: "on_track", label: "順調", tone: "bg-emerald-100 text-emerald-700" },
  { value: "at_risk", label: "要注意", tone: "bg-amber-100 text-amber-700" },
  { value: "off_track", label: "遅延", tone: "bg-rose-100 text-rose-700" },
  { value: "done", label: "完了", tone: "bg-slate-200 text-slate-700" },
];

function currentPeriod(): string {
  const now = new Date();
  const q = Math.floor(now.getMonth() / 3) + 1;
  return `${now.getFullYear()}-Q${q}`;
}

function emptyDraft(): GoalPayload {
  return {
    period: currentPeriod(),
    objective: "",
    key_results: [""],
    progress_pct: 0,
    status: "on_track",
  };
}

function toPayload(g: MyGoal): GoalPayload {
  return {
    id: g.id,
    period: g.period,
    objective: g.objective,
    key_results: g.key_results.length > 0 ? g.key_results : [""],
    progress_pct: g.progress_pct,
    status: g.status,
  };
}

export default function MyGoals() {
  const qc = useQueryClient();
  const goalsQ = useQuery({ queryKey: ["me", "goals"], queryFn: meApi.goals });

  const [editingId, setEditingId] = useState<string | "new" | null>(null);
  const [draft, setDraft] = useState<GoalPayload>(emptyDraft());

  const startEdit = (g: MyGoal) => {
    setEditingId(g.id);
    setDraft(toPayload(g));
  };
  const startNew = () => {
    setEditingId("new");
    setDraft(emptyDraft());
  };
  const cancel = () => {
    setEditingId(null);
    setDraft(emptyDraft());
  };

  const saveM = useMutation({
    mutationFn: async () => {
      if (editingId === "new") return meApi.createGoal(draft);
      return meApi.updateGoal(editingId!, draft);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me", "goals"] });
      cancel();
    },
  });

  const deleteM = useMutation({
    mutationFn: (goalId: string) => meApi.deleteGoal(goalId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me", "goals"] }),
  });

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl sm:text-2xl font-bold">マイ目標 (OKR)</h1>
        {editingId === null && (
          <button onClick={startNew} className="btn-primary flex items-center gap-1">
            <Plus size={16} />
            新規
          </button>
        )}
      </div>

      {editingId === "new" && (
        <GoalEditor
          title="新しい目標"
          draft={draft}
          setDraft={setDraft}
          onSave={() => saveM.mutate()}
          onCancel={cancel}
          saving={saveM.isPending}
        />
      )}

      {goalsQ.isLoading && <p className="text-slate-500">読み込み中…</p>}
      {goalsQ.data && goalsQ.data.goals.length === 0 && editingId !== "new" && (
        <p className="text-slate-500">まだ目標がありません。「新規」から追加できます。</p>
      )}

      <div className="grid gap-3">
        {goalsQ.data?.goals.map((g) =>
          editingId === g.id ? (
            <GoalEditor
              key={g.id}
              title="目標を編集"
              draft={draft}
              setDraft={setDraft}
              onSave={() => saveM.mutate()}
              onCancel={cancel}
              saving={saveM.isPending}
            />
          ) : (
            <GoalCard
              key={g.id}
              goal={g}
              onEdit={() => startEdit(g)}
              onDelete={() => {
                if (confirm(`「${g.objective}」を削除しますか？`)) deleteM.mutate(g.id);
              }}
            />
          ),
        )}
      </div>
    </div>
  );
}

function GoalCard({
  goal,
  onEdit,
  onDelete,
}: {
  goal: MyGoal;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const statusTone = STATUS_OPTIONS.find((s) => s.value === goal.status)?.tone ?? "bg-slate-100";
  const statusLabel = STATUS_OPTIONS.find((s) => s.value === goal.status)?.label ?? goal.status;
  return (
    <article className="card">
      <header className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-2 mb-2">
        <h2 className="font-semibold">{goal.objective}</h2>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-slate-500">{goal.period}</span>
          <span className={`pill ${statusTone}`}>{statusLabel}</span>
          <button onClick={onEdit} className="btn-ghost text-xs flex items-center gap-1">
            <Pencil size={12} /> 編集
          </button>
          <button
            onClick={onDelete}
            className="btn-ghost text-xs flex items-center gap-1 text-rose-700"
          >
            <Trash2 size={12} /> 削除
          </button>
        </div>
      </header>
      <div className="mt-1">
        <div className="h-2 bg-slate-100 rounded">
          <div
            className="h-full bg-brand rounded"
            style={{ width: `${Math.min(100, Math.max(0, goal.progress_pct))}%` }}
          />
        </div>
        <p className="text-xs text-slate-500 mt-1">{goal.progress_pct}%</p>
      </div>
      <div className="mt-3">
        <p className="text-xs text-slate-500 mb-1">Key Results</p>
        <ul className="text-sm list-disc ml-5">
          {goal.key_results.map((kr, i) => (
            <li key={i}>{kr}</li>
          ))}
        </ul>
      </div>
    </article>
  );
}

function GoalEditor({
  title,
  draft,
  setDraft,
  onSave,
  onCancel,
  saving,
}: {
  title: string;
  draft: GoalPayload;
  setDraft: (d: GoalPayload) => void;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
}) {
  const [krs, setKrs] = useState<string[]>(
    draft.key_results.length > 0 ? draft.key_results : [""],
  );
  useEffect(() => {
    setKrs(draft.key_results.length > 0 ? draft.key_results : [""]);
  }, [draft.id]);

  const commit = (next: Partial<GoalPayload>) => setDraft({ ...draft, ...next });

  const updateKr = (i: number, v: string) => {
    const next = [...krs];
    next[i] = v;
    setKrs(next);
    commit({ key_results: next });
  };
  const addKr = () => {
    const next = [...krs, ""];
    setKrs(next);
    commit({ key_results: next });
  };
  const removeKr = (i: number) => {
    const next = krs.filter((_, idx) => idx !== i);
    setKrs(next);
    commit({ key_results: next });
  };

  const canSave = draft.objective.trim().length > 0 && !saving;

  return (
    <article className="card border-brand">
      <h2 className="font-semibold mb-3">{title}</h2>
      <div className="grid gap-3">
        <label className="grid gap-1">
          <span className="text-xs text-slate-500">Objective</span>
          <input
            value={draft.objective}
            onChange={(e) => commit({ objective: e.target.value })}
            className="border border-slate-300 rounded px-3 py-2"
            placeholder="例: チームの 1on1 サイクルとオンボーディング体験を改善する"
          />
        </label>

        <div className="grid sm:grid-cols-3 gap-3">
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">期間</span>
            <input
              value={draft.period}
              onChange={(e) => commit({ period: e.target.value })}
              className="border border-slate-300 rounded px-3 py-2"
              placeholder="2026-Q2"
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">ステータス</span>
            <select
              value={draft.status}
              onChange={(e) => commit({ status: e.target.value })}
              className="border border-slate-300 rounded px-3 py-2"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">進捗 {draft.progress_pct}%</span>
            <input
              type="range"
              min={0}
              max={100}
              value={draft.progress_pct}
              onChange={(e) => commit({ progress_pct: Number(e.target.value) })}
            />
          </label>
        </div>

        <div className="grid gap-2">
          <span className="text-xs text-slate-500">Key Results</span>
          {krs.map((kr, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                value={kr}
                onChange={(e) => updateKr(i, e.target.value)}
                className="flex-1 border border-slate-300 rounded px-3 py-2"
                placeholder={`KR ${i + 1}`}
              />
              <button
                type="button"
                onClick={() => removeKr(i)}
                className="text-slate-500 hover:text-rose-700"
                title="削除"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={addKr}
            className="btn-ghost text-xs self-start flex items-center gap-1"
          >
            <Plus size={12} /> KR を追加
          </button>
        </div>

        <div className="flex items-center gap-2 pt-2">
          <button onClick={onSave} disabled={!canSave} className="btn-primary flex items-center gap-1">
            <Save size={14} />
            {saving ? "保存中…" : "保存"}
          </button>
          <button onClick={onCancel} className="btn-ghost flex items-center gap-1">
            <X size={14} /> キャンセル
          </button>
        </div>
      </div>
    </article>
  );
}
