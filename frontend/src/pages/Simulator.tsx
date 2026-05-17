import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api, type StructureChange } from "@/lib/api";
import { pickText } from "@/lib/format";

const KIND_OPTIONS = [
  { value: "split_team", label: "チーム分割 (split_team)" },
  { value: "merge_teams", label: "チーム統合 (merge_teams)" },
  { value: "move_member", label: "メンバー異動 (move_member)" },
  { value: "change_manager", label: "上司・メンター変更 (change_manager)" },
  { value: "promote", label: "昇進・役割変更 (promote)" },
  { value: "hire", label: "新規採用 (hire)" },
  { value: "other", label: "その他 (other)" },
];

const PRESETS: { name: string; change: StructureChange }[] = [
  {
    name: "プラットフォームチームを SRE / Backend に分割",
    change: {
      kind: "split_team",
      description: "プラットフォームチームを SRE / Backend の 2 つに分け、それぞれに Tech Lead を配置",
      parameters: {
        team_a_members: ["mem001"],
        team_b_members: ["mem002", "mem003", "mem004"],
      },
    },
  },
  {
    name: "新卒のメンターを Senior から Tech Lead に変更",
    change: {
      kind: "change_manager",
      description: "渡辺 翔 (mem004) のメンターを 鈴木 (mem002) から 佐藤 (mem001) に変更",
      parameters: { member_id: "mem004", new_mentor: "mem001" },
    },
  },
  {
    name: "鈴木 亮を Product Growth チームへ異動",
    change: {
      kind: "move_member",
      description: "鈴木 亮 (mem002) を Product Growth チームへ異動",
      parameters: { member_id: "mem002", destination: "Product Growth" },
    },
  },
];

export default function SimulatorPage() {
  const membersQ = useQuery({ queryKey: ["members"], queryFn: api.listMembers });

  const [kind, setKind] = useState<string>("change_manager");
  const [description, setDescription] = useState<string>("");
  const [affectedMemberIds, setAffectedMemberIds] = useState<string[]>([]);
  const [paramJson, setParamJson] = useState<string>("{}");

  const simM = useMutation({
    mutationFn: () => {
      let parameters: Record<string, string | string[]> = {};
      try {
        parameters = paramJson.trim() ? JSON.parse(paramJson) : {};
      } catch {
        parameters = {};
      }
      if (affectedMemberIds.length > 0) {
        parameters["affected_members"] = affectedMemberIds;
      }
      return api.simulate({ kind, description, parameters });
    },
  });

  const loadPreset = (p: (typeof PRESETS)[number]) => {
    setKind(p.change.kind);
    setDescription(p.change.description);
    setParamJson(JSON.stringify(p.change.parameters ?? {}, null, 2));
    const affected = (p.change.parameters?.affected_members as string[]) ?? [];
    setAffectedMemberIds(Array.isArray(affected) ? affected : []);
  };

  useEffect(() => {
    if (!description) loadPreset(PRESETS[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleMember = (id: string) => {
    setAffectedMemberIds((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id],
    );
  };

  const canSubmit = !!description.trim() && !simM.isPending;

  return (
    <div className="grid gap-4 sm:gap-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold">Org Impact Simulator</h1>
        <p className="text-sm text-slate-500 mt-1">
          体制変更案を入力すると、Foundry の Prompt Flow が 4 軸（コミュニケーション・知識・負荷・タイムライン）で並列に分析します。
        </p>
      </div>

      <section className="card">
        <h2 className="font-semibold mb-3">変更案を記述</h2>
        <div className="grid gap-3">
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">変更の種類</span>
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value)}
              className="border border-slate-300 rounded px-3 py-2"
            >
              {KIND_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>

          <label className="grid gap-1">
            <span className="text-xs text-slate-500">
              内容（自由記述・できるだけ具体的に）
            </span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="例: 渡辺 翔 のメンターを 鈴木 から 佐藤 に変更し、3 か月でフロントエンドからインフラへ移籍させる"
              className="w-full h-24 border border-slate-300 rounded p-2 text-sm"
            />
          </label>

          <div className="grid gap-1">
            <span className="text-xs text-slate-500">関係するメンバー（複数選択可）</span>
            <div className="flex flex-wrap gap-2">
              {(membersQ.data?.members ?? []).map((m) => {
                const selected = affectedMemberIds.includes(m.id);
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => toggleMember(m.id)}
                    className={`px-3 py-1.5 rounded-full text-xs border transition ${
                      selected
                        ? "bg-brand text-white border-brand"
                        : "bg-white text-slate-700 border-slate-300 hover:bg-slate-100"
                    }`}
                  >
                    {m.name}
                  </button>
                );
              })}
            </div>
          </div>

          <details className="text-xs text-slate-500">
            <summary className="cursor-pointer">詳細パラメータ（任意・JSON）</summary>
            <textarea
              value={paramJson}
              onChange={(e) => setParamJson(e.target.value)}
              className="mt-2 w-full h-24 border border-slate-300 rounded p-2 font-mono"
              placeholder='{"team_a_members": ["mem001"]}'
            />
          </details>

          <div className="flex flex-wrap items-center gap-2">
            <button onClick={() => simM.mutate()} disabled={!canSubmit} className="btn-primary">
              {simM.isPending ? "シミュレーション中… (~15s)" : "影響を予測"}
            </button>
            {simM.isError && (
              <span className="text-sm text-rose-700">
                {(simM.error as Error).message || "失敗しました"}
              </span>
            )}
          </div>
        </div>
      </section>

      <section>
        <h2 className="font-semibold text-sm text-slate-500 mb-2">サンプルから読み込む</h2>
        <div className="grid gap-2 sm:grid-cols-3">
          {PRESETS.map((p, i) => (
            <button
              key={i}
              onClick={() => loadPreset(p)}
              className="card text-left text-sm hover:shadow-md transition"
            >
              {p.name}
              <p className="text-xs text-slate-400 mt-1">{p.change.kind}</p>
            </button>
          ))}
        </div>
      </section>

      {simM.data && <SimulationView result={simM.data} />}
    </div>
  );
}

const RISK_TONE: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-rose-100 text-rose-700",
};

function SimulationView({ result }: { result: any }) {
  const { impact, members } = result;
  const source = impact?._source;
  return (
    <div className="grid gap-3">
      {impact.overall_risk_level && (
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
          <span className={`pill ${RISK_TONE[impact.overall_risk_level] ?? ""}`}>
            総合リスク: {impact.overall_risk_level}
          </span>
          {source && <span className="text-xs text-slate-500">経路: {source}</span>}
          <p className="text-sm text-slate-700">{impact.summary}</p>
        </div>
      )}

      <Block title="コミュニケーション経路への影響">
        {(impact.communication_impacts ?? []).map((c: any, i: number) => {
          const pair = typeof c.pair === "string"
            ? c.pair
            : [c.pair?.a, c.pair?.b]
                .filter(Boolean)
                .map((id: string) => members[id] ?? id)
                .join(" ↔ ");
          return (
            <li key={i}>
              <span className="font-medium">{pair}</span>: {pickText(c.change)}
              {c.evidence && (
                <span className="text-xs text-slate-400 ml-1">({pickText(c.evidence)})</span>
              )}
            </li>
          );
        })}
      </Block>

      <Block title="知識/単一障害点リスク">
        {(impact.knowledge_risks ?? []).map((r: any, i: number) => (
          <li key={i}>
            <strong>{pickText(r.area)}</strong>
            {r.current_owners && (
              <>
                {" "}— 現オーナー:{" "}
                {(r.current_owners ?? [])
                  .map((id: string) => members[id] ?? id)
                  .join(", ")}
              </>
            )}
            <br />
            <span className="text-rose-700 text-sm">{pickText(r.risk_after_change)}</span>
            {r.evidence && (
              <span className="text-xs text-slate-400 ml-1">({pickText(r.evidence)})</span>
            )}
          </li>
        ))}
      </Block>

      <Block title="ワークロード変化">
        {(impact.workload_shifts ?? []).map((w: any, i: number) => (
          <li key={i}>
            <strong>{members[w.member] ?? w.member}</strong>: {pickText(w.before)} →{" "}
            {pickText(w.after)}{" "}
            <span className="text-xs text-slate-400">({pickText(w.magnitude)})</span>
          </li>
        ))}
      </Block>

      <Block title="移行スケジュール推奨">
        {(impact.timeline_recommendation ?? []).map((t: any, i: number) => (
          <li key={i}>
            <strong>
              {t.phase} ({t.weeks} 週間)
            </strong>
            <ul className="ml-4 list-[circle]">
              {t.actions?.map((a: string, j: number) => (
                <li key={j} className="text-sm">
                  {a}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </Block>
    </div>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <h3 className="font-medium text-sm text-brand mb-2">{title}</h3>
      <ul className="list-disc ml-5 text-sm grid gap-1">{children}</ul>
    </div>
  );
}
