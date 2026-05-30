import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronRight,
  MessageSquare,
  Pin,
  PinOff,
  Send,
  Sparkles,
  Trash2,
  Wand2,
  Wrench,
} from "lucide-react";
import ReactMarkdown from "react-markdown";

import { api, type ChatMessage, type ToolCallTrace } from "@/lib/api";
import { InlineAlert, PageHeader, formatJpDate } from "@/components/ui";

const STARTERS = [
  "今、最も注意して見るべきメンバーは誰ですか？",
  "渡辺さんの 1on1 で聞くべきことを 3 つ教えてください",
  "今期の OKR で進捗が遅れているのは？",
  "今週のチームの健康状態を 100 字で要約してください",
];

const CUSTOM_KEY = "custom";

export default function ChatPage() {
  const qc = useQueryClient();
  const stylesQ = useQuery({ queryKey: ["chat-styles"], queryFn: api.chatStyles });
  const historyQ = useQuery({
    queryKey: ["chat-history"],
    queryFn: api.chatHistory,
    refetchOnWindowFocus: false,
  });
  const presets = stylesQ.data?.styles ?? [];

  interface DisplayMessage extends ChatMessage {
    tool_calls?: ToolCallTrace[];
  }
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [draft, setDraft] = useState("");
  const [style, setStyle] = useState<string>("standard");
  const [customInstructions, setCustomInstructions] = useState<string>("");
  const [styleToast, setStyleToast] = useState<string | null>(null);

  useEffect(() => {
    if (historyLoaded || historyQ.isLoading || !historyQ.isSuccess) return;
    const h = historyQ.data;
    if (h && h.messages.length > 0) {
      setMessages(
        h.messages.map((m) => ({
          role: m.role,
          content: m.content,
          tool_calls: m.tool_calls,
        })),
      );
    }
    if (h?.style) setStyle(h.style);
    if (h?.style_instructions) setCustomInstructions(h.style_instructions);
    setHistoryLoaded(true);
  }, [historyQ.data, historyQ.isLoading, historyQ.isSuccess, historyLoaded]);

  const changeStyle = (key: string, label: string) => {
    setStyle(key);
    setStyleToast(`「${label}」スタイルを選択しました。次の回答から適用されます。`);
    setTimeout(() => setStyleToast(null), 2500);
  };
  const scrollRef = useRef<HTMLDivElement>(null);

  const sendM = useMutation({
    mutationFn: (history: ChatMessage[]) =>
      api.chat({
        messages: history,
        style,
        style_instructions: style === CUSTOM_KEY ? customInstructions : undefined,
      }),
    onSuccess: (data) => {
      setMessages((prev) => {
        const next = [
          ...prev,
          {
            role: "assistant" as const,
            content: data.reply,
            tool_calls: data.tool_calls,
          },
        ];
        qc.setQueryData(["chat-history"], (old: { updated_at?: string | null } | undefined) => ({
          ...(typeof old === "object" && old ? old : {}),
          messages: next,
          style,
          style_instructions: style === CUSTOM_KEY ? customInstructions : null,
          updated_at: new Date().toISOString(),
        }));
        return next;
      });
    },
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, sendM.isPending]);

  const send = (text: string) => {
    const content = text.trim();
    if (!content || sendM.isPending) return;
    if (style === CUSTOM_KEY && !customInstructions.trim()) return;
    const next: DisplayMessage[] = [...messages, { role: "user", content }];
    setMessages(next);
    setDraft("");
    const sendable: ChatMessage[] = next.map(({ role, content }) => ({ role, content }));
    sendM.mutate(sendable);
  };

  const clearHistoryM = useMutation({
    mutationFn: () => api.clearChatHistory(),
    onSuccess: () => {
      qc.setQueryData(["chat-history"], {
        messages: [],
        style: "standard",
        style_instructions: null,
        updated_at: null,
      });
    },
  });

  const reset = async () => {
    if (messages.length > 0 && !confirm("会話履歴を削除しますか？")) return;
    try {
      await clearHistoryM.mutateAsync();
    } catch {
      // still clear locally if server fails
    }
    setMessages([]);
    setDraft("");
    setHistoryLoaded(true);
    sendM.reset();
  };

  const empty = messages.length === 0 && !sendM.isPending;

  return (
    <div className="grid gap-4">
      <PageHeader
        title="AI アシスタント"
        subtitle="チームの最新スナップショットを参照しながら、自由に質問できます。会話は自動で保存され、次回も続きから使えます。"
        actions={
          <div className="flex flex-col items-end gap-1">
            {historyQ.data?.updated_at && (
              <span className="text-[11px] text-slate-400">
                保存 {formatJpDate(historyQ.data.updated_at)}
              </span>
            )}
            <button
              onClick={() => void reset()}
              className="btn-ghost btn-xs"
              disabled={messages.length === 0 || clearHistoryM.isPending}
            >
              <Trash2 size={12} /> 履歴クリア
            </button>
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[300px_1fr] xl:grid-cols-[320px_1fr]">
        {/* ----- left rail: style + starters ----- */}
        <aside className="grid gap-4 lg:sticky lg:top-20 lg:self-start">
          <section className="card">
            <h2 className="eyebrow mb-2 flex items-center gap-1">
              <Wand2 size={12} /> 回答スタイル
            </h2>
            <div className="flex flex-wrap gap-2">
              {presets.map((p) => (
                <StyleChip
                  key={p.key}
                  label={p.label}
                  active={style === p.key}
                  onClick={() => changeStyle(p.key, p.label)}
                />
              ))}
              <StyleChip
                label="カスタム"
                active={style === CUSTOM_KEY}
                onClick={() => changeStyle(CUSTOM_KEY, "カスタム")}
              />
            </div>
            {styleToast && (
              <div className="mt-2">
                <InlineAlert tone="info">{styleToast}</InlineAlert>
              </div>
            )}
            {style === CUSTOM_KEY && (
              <div className="mt-3">
                <label className="label">カスタム指示</label>
                <textarea
                  value={customInstructions}
                  onChange={(e) => setCustomInstructions(e.target.value)}
                  placeholder={
                    "例: 全て表形式 (Markdown) で。1 行目に結論、2 行目に根拠を必ず書く。"
                  }
                  className="textarea font-mono"
                  style={{ minHeight: 110 }}
                />
                <p className="text-xs text-amber-700 mt-1">
                  ※ カスタム指示を入力してから質問してください。
                </p>
              </div>
            )}
          </section>

          <section className="card">
            <h2 className="eyebrow mb-2 flex items-center gap-1">
              <Sparkles size={12} /> よく聞かれる質問
            </h2>
            <div className="grid gap-2">
              {STARTERS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => send(s)}
                  className="text-left text-xs leading-relaxed border border-slate-200 rounded-lg p-2.5 hover:bg-brand/5 hover:border-brand/30 transition"
                >
                  {s}
                </button>
              ))}
            </div>
          </section>

          <FocusMembersPanel />
        </aside>

        {/* ----- right: chat thread + composer ----- */}
        <div className="grid grid-rows-[1fr_auto] gap-3 min-h-[calc(100vh-220px)]">
          <section
            ref={scrollRef}
            className="card overflow-y-auto scroll-area"
            style={{ minHeight: 360 }}
          >
            {empty && (
              <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 gap-3 py-10">
                <span className="grid place-items-center w-12 h-12 rounded-2xl bg-brand-gradient text-white shadow-pop">
                  <MessageSquare size={20} />
                </span>
                <div className="grid gap-1">
                  <p className="text-sm font-medium text-slate-700">
                    会話を始めましょう
                  </p>
                  <p className="text-xs text-slate-500">
                    左の「よく聞かれる質問」から選ぶか、下に直接入力してください。
                  </p>
                </div>
              </div>
            )}

            {!empty && (
              <div className="grid gap-3">
                {messages.map((m, i) => (
                  <div key={i} className="grid gap-1">
                    {m.tool_calls && m.tool_calls.length > 0 && (
                      <ToolCallsBlock calls={m.tool_calls} />
                    )}
                    <Bubble role={m.role} content={m.content} />
                  </div>
                ))}
                {sendM.isPending && <Bubble role="assistant" content="..." pending />}
                {sendM.isError && (
                  <InlineAlert tone="error">
                    {(sendM.error as Error).message || "送信失敗"}
                  </InlineAlert>
                )}
              </div>
            )}
          </section>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(draft);
            }}
            className="card flex gap-2 items-end"
          >
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  send(draft);
                }
              }}
              placeholder="質問を入力（⌘/Ctrl + Enter で送信）"
              className="textarea flex-1"
              style={{ minHeight: 80, maxHeight: 200 }}
            />
            <button
              type="submit"
              className="btn-primary"
              disabled={
                !draft.trim() ||
                sendM.isPending ||
                (style === CUSTOM_KEY && !customInstructions.trim())
              }
            >
              <Send size={14} /> 送信
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

function StyleChip({
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
      className={`px-3 py-1.5 rounded-full text-xs border transition ${
        active
          ? "bg-brand text-white border-brand shadow-sm"
          : "bg-white text-slate-700 border-slate-300 hover:bg-slate-100 hover:border-slate-400"
      }`}
    >
      {label}
    </button>
  );
}

function ToolCallsBlock({ calls }: { calls: ToolCallTrace[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="text-xs">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-700"
      >
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <Wrench size={12} className="text-brand" />
        <span>AI が {calls.length} 件の情報を参照しました</span>
      </button>
      {open && (
        <ul className="mt-2 grid gap-1 ml-4">
          {calls.map((c, i) => (
            <li key={i} className="border border-slate-200 rounded-lg p-2 bg-slate-50">
              <div className="font-mono text-[11px] text-brand-dark">
                {c.name}(
                {Object.keys(c.arguments).length > 0 ? formatArgs(c.arguments) : ""})
              </div>
              <div className="text-[11px] text-slate-500">
                {c.elapsed_ms} ms · {c.result_preview.length} 字 returned
              </div>
              <details className="mt-1">
                <summary className="cursor-pointer text-slate-500">結果プレビュー</summary>
                <pre className="text-[10px] mt-1 whitespace-pre-wrap break-words font-mono text-slate-600">
                  {c.result_preview}
                </pre>
              </details>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function formatArgs(args: Record<string, unknown>): string {
  return Object.entries(args)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(", ");
}

function FocusMembersPanel() {
  const qc = useQueryClient();
  const membersQ = useQuery({
    queryKey: ["members"],
    queryFn: api.listMembers,
    staleTime: 60_000,
  });
  const memoryQ = useQuery({
    queryKey: ["agent-memory"],
    queryFn: api.agentMemory,
    staleTime: 30_000,
  });
  const [picker, setPicker] = useState("");
  const [reason, setReason] = useState("");

  const addM = useMutation({
    mutationFn: () =>
      api.addMemoryFocus(picker, reason || "EM 注目"),
    onSuccess: (m) => {
      qc.setQueryData(["agent-memory"], m);
      setPicker("");
      setReason("");
    },
  });
  const removeM = useMutation({
    mutationFn: (mid: string) => api.removeMemoryFocus(mid),
    onSuccess: (m) => qc.setQueryData(["agent-memory"], m),
  });

  const memberById = new Map(
    (membersQ.data?.members ?? []).map((p) => [p.id, p.name]),
  );
  const focus = memoryQ.data?.focus_members ?? [];

  return (
    <section className="card">
      <h2 className="eyebrow mb-2 flex items-center gap-1">
        <Pin size={12} /> 注目しているメンバー
      </h2>
      <p className="text-[11px] text-slate-500 mb-2 leading-relaxed">
        ここに登録すると、AI アシスタントと日報サマリーが共通の関心事として扱います。
      </p>

      <ul className="grid gap-1.5 mb-2">
        {focus.length === 0 && (
          <li className="text-xs text-slate-400">登録なし</li>
        )}
        {focus.map((f) => (
          <li
            key={f.member_id}
            className="flex items-center justify-between gap-2 text-xs border border-slate-200 rounded-md px-2 py-1.5 bg-white"
          >
            <div className="min-w-0">
              <div className="font-medium text-slate-800 truncate">
                {memberById.get(f.member_id) ?? f.member_id}
              </div>
              {f.reason && (
                <div className="text-[10px] text-slate-500 truncate">
                  {f.reason}
                </div>
              )}
            </div>
            <button
              onClick={() => removeM.mutate(f.member_id)}
              className="text-slate-400 hover:text-rose-600 transition"
              title="登録を外す"
            >
              <PinOff size={12} />
            </button>
          </li>
        ))}
      </ul>

      <div className="grid gap-1.5">
        <select
          value={picker}
          onChange={(e) => setPicker(e.target.value)}
          className="input-sm text-xs"
        >
          <option value="">メンバーを選ぶ…</option>
          {(membersQ.data?.members ?? [])
            .filter((m) => !focus.find((f) => f.member_id === m.id))
            .map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.id})
              </option>
            ))}
        </select>
        <input
          type="text"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="理由 (任意・例: 離職リスク確認)"
          className="input-sm text-xs"
        />
        <button
          onClick={() => addM.mutate()}
          disabled={!picker || addM.isPending}
          className="btn-secondary btn-xs"
        >
          {addM.isPending ? "登録中…" : "注目に追加"}
        </button>
      </div>
    </section>
  );
}

function Bubble({
  role,
  content,
  pending,
}: {
  role: ChatMessage["role"];
  content: string;
  pending?: boolean;
}) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-fade-in`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm ${
          isUser
            ? "bg-brand text-white whitespace-pre-wrap rounded-br-sm"
            : pending
              ? "bg-slate-100 text-slate-400 animate-pulse whitespace-pre-wrap rounded-bl-sm"
              : "bg-slate-100 text-slate-800 rounded-bl-sm"
        }`}
      >
        {isUser || pending ? (
          content
        ) : (
          <div className="prose prose-sm max-w-none prose-headings:font-semibold prose-headings:text-slate-800 prose-strong:text-slate-800 prose-ul:my-1 prose-li:my-0 prose-p:my-1">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
