import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  CircleSlash,
  History,
  Loader2,
  PlayCircle,
} from "lucide-react";

import {
  api,
  type InsightAction,
  type InsightActionStatus,
} from "@/lib/api";
import {
  EmptyState,
  InlineAlert,
  PageHeader,
  SectionHeader,
  SkeletonCard,
  formatJpDate,
} from "@/components/ui";

const STATUS_META: Record<
  InsightActionStatus,
  { label: string; icon: React.ReactNode; cls: string }
> = {
  open: {
    label: "未着手",
    icon: <AlertTriangle size={11} />,
    cls: "bg-amber-100 text-amber-700 border-amber-200",
  },
  in_progress: {
    label: "対応中",
    icon: <Activity size={11} />,
    cls: "bg-sky-100 text-sky-700 border-sky-200",
  },
  resolved: {
    label: "解決",
    icon: <CheckCircle2 size={11} />,
    cls: "bg-emerald-100 text-emerald-700 border-emerald-200",
  },
  wont_fix: {
    label: "対応見送り",
    icon: <CircleSlash size={11} />,
    cls: "bg-slate-100 text-slate-600 border-slate-200",
  },
};

const STATUS_ORDER: InsightActionStatus[] = [
  "open",
  "in_progress",
  "resolved",
  "wont_fix",
];

const SIGNAL_KIND_LABEL: Record<string, string> = {
  retention: "離職リスク",
  friction: "対人摩擦",
  capacity: "過負荷",
  engagement: "エンゲージメント",
  health: "コンディション",
};

export default function FollowupsPage() {
  const [filter, setFilter] = useState<"all" | InsightActionStatus>("all");
  const qc = useQueryClient();
  const listQ = useQuery({
    queryKey: ["insight-actions", filter],
    queryFn: () =>
      api.listInsightActions(filter === "all" ? undefined : { status: filter }),
    staleTime: 10_000,
  });

  const updateM = useMutation({
    mutationFn: (input: {
      id: string;
      status?: InsightActionStatus;
      note?: string;
    }) =>
      api.updateInsightAction(input.id, {
        status: input.status,
        note: input.note,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insight-actions"] }),
  });

  const counts = useMemo(() => {
    const all = listQ.data?.actions ?? [];
    return {
      total: all.length,
      open: all.filter((a) => a.status === "open").length,
      in_progress: all.filter((a) => a.status === "in_progress").length,
      resolved: all.filter((a) => a.status === "resolved").length,
    };
  }, [listQ.data]);

  return (
    <div className="grid gap-6">
      <PageHeader
        title="フォローアップ"
        subtitle="AI が示唆したシグナル（離職リスク・対人摩擦・成長停滞など）に対して、EM がどのように動いたかを記録し PDCA を回します。"
      />

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <FilterTab
          label={`全て (${counts.total})`}
          active={filter === "all"}
          onClick={() => setFilter("all")}
        />
        {STATUS_ORDER.map((s) => (
          <FilterTab
            key={s}
            label={`${STATUS_META[s].label}${s === "open" ? ` (${counts.open})` : s === "in_progress" ? ` (${counts.in_progress})` : s === "resolved" ? ` (${counts.resolved})` : ""}`}
            active={filter === s}
            onClick={() => setFilter(s)}
          />
        ))}
      </div>

      <section className="grid gap-3">
        <SectionHeader
          icon={<History size={16} className="text-brand" />}
          title="追跡中のアクション"
          subtitle="日報サマリーや AI アシスタントが示したシグナルから、ここに作成できます"
        />

        {listQ.isLoading && <SkeletonCard lines={3} />}
        {!listQ.isLoading && listQ.isError && (
          <InlineAlert tone="error">
            一覧の取得に失敗しました: {(listQ.error as Error).message}
          </InlineAlert>
        )}
        {!listQ.isLoading && (listQ.data?.actions?.length ?? 0) === 0 && (
          <EmptyState
            icon={<AlertTriangle size={28} />}
            title="まだ追跡中のアクションはありません"
            description="日報サマリー (期間サマリー) の「注視すべきシグナル」横の『アクションを追跡』から登録できます。"
          />
        )}

        {(listQ.data?.actions ?? []).map((a) => (
          <ActionCard
            key={a.id}
            action={a}
            onTransition={(status, note) =>
              updateM.mutate({ id: a.id, status, note })
            }
            disabled={updateM.isPending}
          />
        ))}
      </section>
    </div>
  );
}

function FilterTab({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full border transition ${
        active
          ? "bg-brand text-white border-brand shadow-sm"
          : "bg-white text-slate-700 border-slate-300 hover:bg-slate-100"
      }`}
    >
      {label}
    </button>
  );
}

function ActionCard({
  action,
  onTransition,
  disabled,
}: {
  action: InsightAction;
  onTransition: (status: InsightActionStatus, note: string) => void;
  disabled: boolean;
}) {
  const [note, setNote] = useState("");
  const meta = STATUS_META[action.status];
  const sigLabel = action.signal_kind
    ? SIGNAL_KIND_LABEL[action.signal_kind] ?? action.signal_kind
    : null;

  const submit = (next: InsightActionStatus) => {
    onTransition(next, note);
    setNote("");
  };

  return (
    <article className="card grid gap-3">
      <header className="flex flex-wrap items-baseline gap-2">
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[11px] font-semibold ${meta.cls}`}
        >
          {meta.icon}
          {meta.label}
        </span>
        {sigLabel && (
          <span className="text-[11px] text-slate-500 pill-amber">
            {sigLabel}
          </span>
        )}
        {action.member_id && (
          <span className="text-[11px] text-slate-500">
            対象: {action.member_id}
          </span>
        )}
        <span className="text-[11px] text-slate-400 ml-auto">
          作成 {action.created_at ? formatJpDate(action.created_at) : "-"} / 更新{" "}
          {action.updated_at ? formatJpDate(action.updated_at) : "-"}
        </span>
      </header>

      <div>
        <h3 className="font-semibold text-slate-900">{action.title}</h3>
        {action.details && (
          <p className="text-sm text-slate-700 mt-1 whitespace-pre-line">
            {action.details}
          </p>
        )}
        {action.evidence_dates && action.evidence_dates.length > 0 && (
          <p className="text-[11px] text-slate-500 mt-1.5">
            根拠日: {action.evidence_dates.join(", ")}
          </p>
        )}
      </div>

      {action.history.length > 1 && (
        <details className="text-xs text-slate-600">
          <summary className="cursor-pointer text-slate-700">
            履歴 ({action.history.length} 件)
          </summary>
          <ul className="grid gap-1.5 mt-2">
            {action.history.map((h, i) => {
              const m = STATUS_META[h.status];
              return (
                <li
                  key={i}
                  className="flex flex-wrap items-baseline gap-2 border-l-2 border-slate-200 pl-2"
                >
                  <span
                    className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] ${m.cls}`}
                  >
                    {m.icon}
                    {m.label}
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {formatJpDate(h.at)} · {h.by}
                  </span>
                  {h.note && (
                    <span className="text-[11px] text-slate-700">{h.note}</span>
                  )}
                </li>
              );
            })}
          </ul>
        </details>
      )}

      <div className="grid gap-2">
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          placeholder="進捗メモ（任意・1on1 で確認した内容など）"
          className="textarea text-sm"
        />
        <div className="flex flex-wrap gap-2">
          {action.status !== "in_progress" && (
            <button
              onClick={() => submit("in_progress")}
              disabled={disabled}
              className="btn-secondary"
            >
              {disabled ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <PlayCircle size={14} />
              )}
              対応中にする
            </button>
          )}
          {action.status !== "resolved" && (
            <button
              onClick={() => submit("resolved")}
              disabled={disabled}
              className="btn-primary"
            >
              <CheckCircle2 size={14} />
              解決にする
            </button>
          )}
          {action.status !== "wont_fix" && action.status !== "resolved" && (
            <button
              onClick={() => submit("wont_fix")}
              disabled={disabled}
              className="btn-ghost"
            >
              <CircleSlash size={14} />
              見送る
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
