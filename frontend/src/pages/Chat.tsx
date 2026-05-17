import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Send, Trash2 } from "lucide-react";

import { api, type ChatMessage } from "@/lib/api";

const STARTERS = [
  "今、最も注意して見るべきメンバーは誰ですか？",
  "渡辺さんの 1on1 で聞くべきことを 3 つ教えてください",
  "今期の OKR で進捗が遅れているのは？",
  "今週のチームの健康状態を 100 字で要約してください",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const sendM = useMutation({
    mutationFn: (history: ChatMessage[]) => api.chat(history),
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

      <div
        ref={scrollRef}
        className="card overflow-y-auto"
        style={{ minHeight: 360, maxHeight: "calc(100vh - 360px)" }}
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
          disabled={!draft.trim() || sendM.isPending}
        >
          <Send size={14} /> 送信
        </button>
      </form>
    </div>
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
