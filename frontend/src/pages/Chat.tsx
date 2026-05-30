import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronRight,
  MessageSquare,
  Send,
  Trash2,
  Wand2,
  Wrench,
} from "lucide-react";
import ReactMarkdown from "react-markdown";

import { api, type ChatMessage, type ToolCallTrace } from "@/lib/api";
import { InlineAlert, PageHeader } from "@/components/ui";

const STARTERS = [
  "今、最も注意して見るべきメンバーは誰ですか？",
  "渡辺さんの 1on1 で聞くべきことを 3 つ教えてください",
  "今期の OKR で進捗が遅れているのは？",
  "今週のチームの健康状態を 100 字で要約してください",
];

const CUSTOM_KEY = "custom";

export default function ChatPage() {
  const stylesQ = useQuery({ queryKey: ["chat-styles"], queryFn: api.chatStyles });
  const presets = stylesQ.data?.styles ?? [];

  interface DisplayMessage extends ChatMessage {
    tool_calls?: ToolCallTrace[];
  }
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [style, setStyle] = useState<string>("standard");
  const [customInstructions, setCustomInstructions] = useState<string>("");
  const [styleToast, setStyleToast] = useState<string | null>(null);

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
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply,
          tool_calls: data.tool_calls,
        },
      ]);
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

  const reset = () => {
    if (messages.length > 0 && !confirm("会話履歴を削除しますか？")) return;
    setMessages([]);
    setDraft("");
    sendM.reset();
  };

  return (
    <div className="grid gap-4 max-w-3xl mx-auto">
      <PageHeader
        title="EM チャット"
        subtitle="チームの最新スナップショットを参照しながら、自由に質問できます。AI は質問に応じて自動的にツールを呼び出します。"
        actions={
          <button
            onClick={reset}
            className="btn-ghost btn-xs"
            disabled={messages.length === 0}
          >
            <Trash2 size={12} /> 履歴クリア
          </button>
        }
      />

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
            <label className="label">
              カスタム指示（口調・長さ・出力フォーマットなど）
            </label>
            <textarea
              value={customInstructions}
              onChange={(e) => setCustomInstructions(e.target.value)}
              placeholder={
                "例: 全て表形式 (Markdown) で。1 行目に結論、2 行目に根拠を必ず書く。\n或いは: コードレビュアー口調で、率直かつ歯切れよく。"
              }
              className="textarea font-mono"
            />
            <p className="text-xs text-amber-700 mt-1">
              ※ カスタム指示を入力してから質問してください。
            </p>
          </div>
        )}
      </section>

      <div
        ref={scrollRef}
        className="card overflow-y-auto scroll-area"
        style={{ minHeight: 360, maxHeight: "calc(100vh - 520px)" }}
      >
        {messages.length === 0 && !sendM.isPending && (
          <div>
            <div className="flex items-center gap-2 text-slate-500 mb-3">
              <MessageSquare size={14} />
              <p className="text-sm">
                よく聞かれる質問から選ぶか、下の入力欄から自由に質問してください。
              </p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {STARTERS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => send(s)}
                  className="text-left text-sm border border-slate-200 rounded-lg p-3 hover:bg-brand/5 hover:border-brand/30 transition"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

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
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
        className="card flex gap-2"
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
          className="btn-primary self-end"
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
