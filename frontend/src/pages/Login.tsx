import { useState } from "react";
import { Compass } from "lucide-react";

import { useLogin } from "@/lib/auth";

const DEMO_ACCOUNTS = [
  { label: "Admin", name: "田中 健", email: "tanaka.ken@atlaslens.dev" },
  { label: "Tech Lead", name: "佐藤 美咲", email: "sato.misaki@atlaslens.dev" },
  { label: "Senior", name: "鈴木 亮", email: "suzuki.ryo@atlaslens.dev" },
  { label: "Mid", name: "山本 由香", email: "yamamoto.yuka@atlaslens.dev" },
  { label: "Junior", name: "渡辺 翔", email: "watanabe.sho@atlaslens.dev" },
  { label: "QA / 大阪", name: "高橋 結衣", email: "takahashi.yui@atlaslens.dev" },
];

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login.mutate({ email, password });
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-slate-50">
      {/* Left rail — brand + value proposition */}
      <div className="hidden lg:flex flex-col justify-between p-12 bg-gradient-to-br from-brand to-brand-dark text-white">
        <div className="flex items-center gap-2">
          <span className="grid place-items-center w-9 h-9 rounded-xl bg-white/15">
            <Compass size={20} />
          </span>
          <span className="text-xl font-bold tracking-tight">AtlasLens</span>
        </div>

        <div className="max-w-md">
          <p className="text-3xl font-semibold leading-snug">
            見えていないものを、<br />
            AI が見続ける。
          </p>
          <p className="mt-4 text-white/80 text-sm leading-relaxed">
            日報・1on1・OKR を横断する Agentic AI が、
            気づきと意思決定を 24 時間支えます。
            Microsoft Azure AI Foundry 上でマルチエージェントが協調動作。
          </p>
          <ul className="mt-6 grid gap-2 text-sm">
            <li className="flex items-start gap-2">
              <span className="mt-1.5 inline-block w-1.5 h-1.5 rounded-full bg-white/70" />
              <span>Chat はツールを自律選択して根拠付きで回答</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-1.5 inline-block w-1.5 h-1.5 rounded-full bg-white/70" />
              <span>シミュレーターは Plan → Critique → Refine で品質を担保</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-1.5 inline-block w-1.5 h-1.5 rounded-full bg-white/70" />
              <span>行動指標のみを見る Responsible-AI 設計</span>
            </li>
          </ul>
        </div>

        <p className="text-xs text-white/60">
          Microsoft Agent Hackathon 2026 powered by Tokyo Electron Device
        </p>
      </div>

      {/* Right rail — login form */}
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-2 mb-6">
            <span className="grid place-items-center w-8 h-8 rounded-lg bg-brand text-white">
              <Compass size={16} />
            </span>
            <span className="text-lg font-bold">AtlasLens</span>
          </div>

          <h1 className="page-title">ログイン</h1>
          <p className="page-subtitle">Team Co-pilot · Azure AI Foundry powered</p>

          <form onSubmit={handleSubmit} className="grid gap-4 mt-6">
            <label className="grid gap-1">
              <span className="label">メールアドレス</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
                className="input"
                placeholder="tanaka.ken@atlaslens.dev"
              />
            </label>
            <label className="grid gap-1">
              <span className="label">パスワード</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                className="input"
                placeholder="••••••••"
              />
            </label>
            {login.isError && (
              <p className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                {(login.error as Error).message || "ログインに失敗しました"}
              </p>
            )}
            <button
              type="submit"
              disabled={login.isPending}
              className="btn-primary w-full mt-2"
            >
              {login.isPending ? "ログイン中…" : "ログイン"}
            </button>
          </form>

          <div className="mt-8 border-t border-slate-200 pt-5">
            <p className="eyebrow mb-3">デモアカウント（クリックでメール反映）</p>
            <div className="grid gap-1.5">
              {DEMO_ACCOUNTS.map((a) => (
                <button
                  key={a.email}
                  type="button"
                  onClick={() => setEmail(a.email)}
                  className="flex items-center justify-between gap-2 text-left text-sm
                             px-3 py-2 rounded-lg border border-slate-200 hover:border-brand/40
                             hover:bg-brand/5 transition"
                >
                  <span className="min-w-0">
                    <span className="font-medium text-slate-800">{a.name}</span>
                    <span className="block text-xs text-slate-500 truncate">{a.email}</span>
                  </span>
                  <span className="pill-slate shrink-0">{a.label}</span>
                </button>
              ))}
            </div>
            <p className="text-xs text-slate-400 mt-3">
              パスワードは申請時に個別にお送りします。お持ちでない場合は運営にお問い合わせください。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
