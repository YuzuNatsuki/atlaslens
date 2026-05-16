import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { api, type StructureChange } from "@/lib/api";
import { pickText } from "@/lib/format";

const PRESETS: StructureChange[] = [
  {
    kind: "split_team",
    description: "プラットフォームチームを SRE / Backend の2チームに分割",
    parameters: {
      team_a_members: ["mem001"],
      team_b_members: ["mem002", "mem003", "mem004"],
    },
  },
  {
    kind: "move_member",
    description: "鈴木 亮 (mem002) を別のプロダクトチームに異動",
    parameters: { member_id: "mem002", destination: "Product Growth" },
  },
  {
    kind: "change_manager",
    description: "渡辺 翔 (mem004) のメンターを 鈴木 (mem002) から 佐藤 (mem001) に変更",
    parameters: { member_id: "mem004", new_mentor: "mem001" },
  },
];

const RISK_TONE: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-rose-100 text-rose-700",
};

export default function SimulatorPage() {
  const [selected, setSelected] = useState<StructureChange>(PRESETS[0]);
  const simM = useMutation({ mutationFn: () => api.simulate(selected) });

  return (
    <div className="grid gap-6">
      <section className="card">
        <h2 className="text-lg font-semibold mb-2">体制変更の候補</h2>
        <div className="grid gap-2">
          {PRESETS.map((p, i) => (
            <label
              key={i}
              className={`flex items-start gap-2 p-2 rounded cursor-pointer ${
                selected === p ? "bg-brand/10" : "hover:bg-slate-100"
              }`}
            >
              <input
                type="radio"
                name="change"
                checked={selected === p}
                onChange={() => setSelected(p)}
                className="mt-1"
              />
              <div>
                <p className="font-medium text-sm">{p.description}</p>
                <p className="text-xs text-slate-500">kind: {p.kind}</p>
              </div>
            </label>
          ))}
        </div>
        <button onClick={() => simM.mutate()} disabled={simM.isPending} className="btn-primary mt-3">
          {simM.isPending ? "シミュレーション中…" : "影響を予測"}
        </button>
      </section>

      {simM.data && <SimulationView result={simM.data} />}
    </div>
  );
}

function SimulationView({ result }: { result: any }) {
  const { impact, members } = result;
  return (
    <div className="grid gap-3">
      {impact.overall_risk_level && (
        <div className="flex items-center gap-3">
          <span className={`pill ${RISK_TONE[impact.overall_risk_level] ?? ""}`}>
            総合リスク: {impact.overall_risk_level}
          </span>
          <p className="text-sm text-slate-700">{impact.summary}</p>
        </div>
      )}

      <Block title="コミュニケーション経路への影響">
        {(impact.communication_impacts ?? []).map((c: any, i: number) => {
          const pair = typeof c.pair === "string"
            ? c.pair
            : [c.pair?.a, c.pair?.b].filter(Boolean).map((id: string) => members[id] ?? id).join(" ↔ ");
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
              <> — 現オーナー: {(r.current_owners ?? []).map((id: string) => members[id] ?? id).join(", ")}</>
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
            <strong>{members[w.member] ?? w.member}</strong>: {pickText(w.before)} → {pickText(w.after)}{" "}
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
