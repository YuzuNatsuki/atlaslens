import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Send, Trash2, Wand2 } from "lucide-react";

import { api, type ChatMessage } from "@/lib/api";

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

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [style, setStyle] = useState<string>("standard");
  const [customInstructions, setCustomInstructions] = useState<string>("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const sendM = useMutation({
    mutationFn: (history: ChatMessage[]) =>
      api.chat({
        messages: history,
        style,
        style_instructions: style === CUSTOM_KEY ? customInstructions : undefined,
      }),
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
    },
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sendM.isPending]);

  const send = (text: string) => {
    const content = text.trim();
    if (!content || sendM.isPending) return;
    if (style === CUSTOM_KEY && !customInstructions.trim()) {
      // Refuse silently — user must give custom instructions.
      return;
    }
    const next: ChatMessage[] = [...messages, { role: "user", content }];
    setMessages(next);
    setDraft("");
    sendM.mutate(next);
  };

  const reset = () => {
    setMessages([]);
    setDraft("");
    sendM.reset();
  };

  return (
    <div className="grid gap-3 sm:gap-4 max-w-3xl mx-auto">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">EM チャット</h1>
          <p className="text-sm text-slate-500">
            チームの最新スナップショットを参照しながら、自由に質問できます。
          </p>
        </div>
        <button
          onClick={reset}
          className="btn-ghost text-xs flex items-center gap-1"
          disabled={messages.length === 0}
        >
          <Trash2 size={12} /> 履歴クリア
        </button>
      </header>

      <section className="card">
        <h2 className="text-xs text-slate-500 mb-2 flex items-center gap-1">
          <Wand2 size={12} /> 回答スタイル
        </h2>
        <div className="flex flex-wrap gap-2">
          {presets.map((p) => (
            <StyleChip
              key={p.key}
              label={p.label}
              active={style === p.key}
              onClick={() => setStyle(p.key)}
            />
          ))}
          <StyleChip
            label="カスタム"
            active={style === CUSTOM_KEY}
            onClick={() => setStyle(CUSTOM_KEY)}
          />
        </div>
        {style === CUSTOM_KEY && (
          <div className="mt-3">
            <label className="text-xs text-slate-500">
              カスタム指示（口調・長さ・出力フォーマットなど）
            </label>
            <textarea
              value={customInstructions}
              onChange={(e) => setCustomInstructions(e.target.value)}
              placeholder={
                "例: 全て表形式 (Markdown) で。1 行目に結論、2 行目に根拠を必ず書く。\n或いは: コードレビュアー口調で、率直かつ歯切れよく。"
              }
              className="mt-1 w-full h-24 border border-slate-300 rounded p-2 text-sm font-mono"
            />
            <p className="text-xs text-amber-700 mt-1">
              ※ カスタム指示を入力してから質問してください。
            </p>
          </div>
        )}
      </section>

      <div
        ref={scrollRef}
        className="card overflow-y-auto"
        style={{ minHeight: 360, maxHeight: "calc(100vh - 480px)" }}
      >
        {messages.length === 0 && !sendM.isPending && (
          <div>
            <p className="text-sm text-slate-500 mb-3">
              よく聞かれる質問から選ぶか、下の入力欄から自由に質問してください。
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {STARTERS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => send(s)}
                  className="text-left text-sm border border-slate-200 rounded-lg p-3 hover:bg-slate-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="grid gap-3">
          {messages.map((m, i) => (
            <Bubble key={i} role={m.role} content={m.content} />
          ))}
          {sendM.isPending && <Bubble role="assistant" content="..." pending />}
          {sendM.isError && (
            <p className="text-sm text-rose-700">
              {(sendM.error as Error).message || "送信失敗"}
            </p>
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
          placeholder="質問を入力 (⌘/Ctrl + Enter で送信)"
          className="flex-1 border border-slate-300 rounded p-2 text-sm h-20 resize-none"
        />
        <button
          type="submit"
          className="btn-primary self-end flex items-center gap-1"
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
          ? "bg-brand text-white border-brand"
          : "bg-white text-slate-700 border-slate-300 hover:bg-slate-100"
      }`}
    >
      {label}
    </button>
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
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
          isUser
            ? "bg-brand text-white"
            : pending
              ? "bg-slate-100 text-slate-400 animate-pulse"
              : "bg-slate-100 text-slate-800"
        }`}
      >
        {content}
      </div>
    </div>
  );
}
