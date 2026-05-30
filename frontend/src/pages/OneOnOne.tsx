import { useParams, Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ArrowLeft, FileText, RefreshCw, Save, Sparkles } from "lucide-react";

import { api } from "@/lib/api";
import { humanizeEvidenceId, pickText } from "@/lib/format";
import {
  EmptyState,
  InlineAlert,
  PageHeader,
  SectionHeader,
  Spinner,
} from "@/components/ui";

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function OneOnOnePage() {
  const { memberId = "" } = useParams<{ memberId: string }>();
  const qc = useQueryClient();
  const memberQ = useQuery({
    queryKey: ["member", memberId],
    queryFn: () => api.getMember(memberId),
    enabled: Boolean(memberId),
  });
  const memberName = memberQ.data?.profile.name;

  const membersQ = useQuery({ queryKey: ["members"], queryFn: api.listMembers });
  const memberIndex: Record<string, string> = Object.fromEntries(
    (membersQ.data?.members ?? []).map((mb) => [mb.id, mb.name]),
  );
  const [rawNotes, setRawNotes] = useState("");
  const [heldOn, setHeldOn] = useState(todayISO());
  const [topics, setTopics] = useState("");
  const [todos, setTodos] = useState("");
  const [followUps, setFollowUps] = useState("");
  const [structuredNotes, setStructuredNotes] = useState("");
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  // Don't auto-fetch — the prep packet costs an LLM call. Trigger via button.
  const packetQ = useQuery({
    queryKey: ["1on1-packet", memberId],
    queryFn: () => api.getOneOnOnePacket(memberId),
    enabled: false,
  });

  const draftM = useMutation({
    mutationFn: () =>
      api.draftMinutes({ member_id: memberId, raw_notes: rawNotes }),
  });

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
  }, [draftM.data]); // eslint-disable-line react-hooks/exhaustive-deps

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
      setSaveMsg(
        "1on1 を記録として保存しました。メンバー側の画面からも閲覧できます。",
      );
      qc.invalidateQueries({ queryKey: ["1on1-packet", memberId] });
    },
  });

  return (
    <div className="grid gap-6">
      <div>
        <Link
          to={memberId ? `/members/${memberId}` : "/"}
          className="meta inline-flex items-center gap-1 hover:text-brand-dark"
        >
          <ArrowLeft size={12} />
          {memberName ? `${memberName} の詳細に戻る` : "メンバー詳細に戻る"}
        </Link>
      </div>

      <PageHeader
        title={memberName ? `${memberName} との 1on1` : "1on1 準備"}
        subtitle="Coach エージェントが事前パケットと議事録整形をサポートします。"
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Step 1 — 事前パケット */}
        <section>
          <SectionHeader
            icon={<Sparkles size={16} className="text-brand" />}
            title="Step 1 — 事前パケット"
            subtitle="OKR / 日報 / 前回 1on1 を横断参照"
            actions={
              <button
                onClick={() => packetQ.refetch()}
                disabled={packetQ.isFetching}
                className="btn-secondary"
              >
                <RefreshCw
                  size={12}
                  className={packetQ.isFetching ? "animate-spin" : ""}
                />
                {packetQ.isFetching
                  ? "生成中… (~10s)"
                  : packetQ.data
                    ? "再生成"
                    : "事前パケットを生成"}
              </button>
            }
          />

          {packetQ.isFetching && (
            <div className="card-muted">
              <Spinner label="AI が直近の活動を確認しています…" />
            </div>
          )}
          {!packetQ.data && !packetQ.isFetching && (
            <EmptyState
              icon={<FileText size={28} />}
              title="まだ事前パケットは生成されていません"
              description="「事前パケットを生成」を押すと、Coach エージェントが OKR・日報・前回 1on1 を読み、議論ポイントと質問例を整理します（10 秒前後）。"
            />
          )}
          {packetQ.data && (
            <div className="grid gap-3">
              {packetQ.data.packet.opening_check_in && (
                <div className="card">
                  <h3 className="font-medium text-sm text-brand-dark mb-1">
                    オープニング
                  </h3>
                  <p className="text-sm">{packetQ.data.packet.opening_check_in}</p>
                </div>
              )}
              <SectionBlock
                title="議論ポイント候補"
                items={(packetQ.data.packet.discussion_topics ?? []).map(
                  (t: any) => ({
                    primary: pickText(t),
                    secondary: Array.isArray(t?.evidence)
                      ? t.evidence
                          .map((id: string) => humanizeEvidenceId(id, memberIndex))
                          .join("、")
                      : undefined,
                  }),
                )}
              />
              <SectionBlock
                title="成長を引き出す質問"
                items={(packetQ.data.packet.growth_questions ?? []).map(
                  (q: any) => ({ primary: pickText(q) }),
                )}
              />
              <SectionBlock
                title="拾い上げるべきブロッカー"
                items={(packetQ.data.packet.blockers_to_surface ?? []).map(
                  (b: any) => ({ primary: pickText(b) }),
                )}
                tone="text-rose-700"
              />
              <SectionBlock
                title="前回からのフォローアップ"
                items={(
                  packetQ.data.packet.follow_ups_from_last_time ?? []
                ).map((f: any) => ({ primary: pickText(f) }))}
              />
            </div>
          )}
        </section>

        {/* Step 2 — 議事録 + 保存 */}
        <section>
          <SectionHeader
            icon={<Save size={16} className="text-brand" />}
            title="Step 2 — 議事録ドラフト + 記録保存"
            subtitle="生メモから AI が要約・ToDo を抽出します"
          />
          <div className="card">
            <label className="label">1on1 中のメモ（生）</label>
            <textarea
              value={rawNotes}
              onChange={(e) => setRawNotes(e.target.value)}
              placeholder={
                "話したことをそのままメモしてください。後で AI が整形します。\n例: OKR 進捗は順調。大阪-東京の時差で朝会に参加しにくいと話していた。次回までに非同期の連絡手段を検討する。"
              }
              className="textarea"
              style={{ minHeight: 120 }}
            />
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <button
                onClick={() => draftM.mutate()}
                disabled={!rawNotes || draftM.isPending}
                className="btn-primary"
              >
                <Sparkles size={14} />
                {draftM.isPending
                  ? "整形中…"
                  : "議事録に整形 + ToDo を抽出"}
              </button>
              {draftM.data && (
                <InlineAlert tone="success">
                  AI が整形しました。下の各フィールドに自動入力されています。
                </InlineAlert>
              )}
              {draftM.isError && (
                <InlineAlert tone="error">
                  整形に失敗しました: {(draftM.error as Error).message}
                </InlineAlert>
              )}
            </div>
          </div>

          <div className="card mt-3">
            <h3 className="section-title mb-2">記録として保存</h3>

            <div className="grid sm:grid-cols-2 gap-3 mb-3">
              <label className="grid gap-1">
                <span className="label">日付</span>
                <input
                  type="date"
                  value={heldOn}
                  onChange={(e) => setHeldOn(e.target.value)}
                  className="input-sm"
                />
              </label>
            </div>

            <Field label="議題 (1行1件)">
              <textarea
                value={topics}
                onChange={(e) => setTopics(e.target.value)}
                placeholder={"例: OKR 進捗確認\nオンコール体制についての相談"}
                className="textarea"
                style={{ minHeight: 60 }}
              />
            </Field>
            <Field label="ノート">
              <textarea
                value={structuredNotes}
                onChange={(e) => setStructuredNotes(e.target.value)}
                placeholder="1on1 の概要・決定事項・気づきをまとめて記録します。"
                className="textarea"
                style={{ minHeight: 90 }}
              />
            </Field>
            <Field label="ToDo (1行1件)">
              <textarea
                value={todos}
                onChange={(e) => setTodos(e.target.value)}
                placeholder={
                  "例: EM: 非同期連絡ルールを来週までに整理する\n本人: SLO ダッシュボードのドラフトを共有する"
                }
                className="textarea"
                style={{ minHeight: 80 }}
              />
            </Field>
            <Field label="フォローアップ (1行1件)">
              <textarea
                value={followUps}
                onChange={(e) => setFollowUps(e.target.value)}
                placeholder={
                  "例: 次回: ドラフト共有の確認\n前回: オンコール候補者の合意形成 → 完了したか確認"
                }
                className="textarea"
                style={{ minHeight: 60 }}
              />
            </Field>

            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <button
                onClick={() => saveM.mutate()}
                disabled={
                  saveM.isPending ||
                  (!structuredNotes.trim() && !rawNotes.trim())
                }
                className="btn-primary"
              >
                <Save size={14} />
                {saveM.isPending ? "保存中…" : "1on1 を保存"}
              </button>
              {saveMsg && (
                <InlineAlert tone="success">{saveMsg}</InlineAlert>
              )}
              {saveM.isError && (
                <InlineAlert tone="error">
                  保存に失敗しました: {(saveM.error as Error).message}
                </InlineAlert>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-2.5">
      <label className="label">{label}</label>
      {children}
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
      <h3 className={`font-medium text-sm mb-1 ${tone ?? "text-slate-700"}`}>
        {title}
      </h3>
      <ul className="text-sm list-disc ml-5 grid gap-1">
        {items.map((it, i) => (
          <li key={i}>
            {it.primary}
            {it.secondary && (
              <span className="text-xs text-slate-400 ml-1">
                （{it.secondary}）
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
