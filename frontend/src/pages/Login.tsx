import { useState } from "react";

import { useLogin } from "@/lib/auth";

const DEMO_ACCOUNTS = [
  { label: "EM: 田中 健", email: "tanaka.ken@atlaslens.dev" },
  { label: "Tech Lead: 佐藤 美咲", email: "sato.misaki@atlaslens.dev" },
  { label: "Senior: 鈴木 亮", email: "suzuki.ryo@atlaslens.dev" },
  { label: "Mid: 山本 由香", email: "yamamoto.yuka@atlaslens.dev" },
  { label: "Junior: 渡辺 翔", email: "watanabe.sho@atlaslens.dev" },
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
    <div className="min-h-screen flex items-center justify-center px-4 py-8 bg-slate-50">
      <div className="w-full max-w-md card">
        <h1 className="text-2xl font-bold text-brand">AtlasLens</h1>
        <p className="text-sm text-slate-500 mb-6">EM-Copilot · Azure AI Foundry powered</p>

        <form onSubmit={handleSubmit} className="grid gap-3">
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">メールアドレス</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
              className="border border-slate-300 rounded px-3 py-2"
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">パスワード</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              className="border border-slate-300 rounded px-3 py-2"
            />
          </label>
          {login.isError && (
            <p className="text-sm text-rose-700">
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

        <div className="mt-6 border-t border-slate-200 pt-4">
          <p className="text-xs text-slate-500 mb-2">デモアカウント（クリックで反映）</p>
          <div className="grid gap-1">
            {DEMO_ACCOUNTS.map((a) => (
              <button
                key={a.email}
                type="button"
                onClick={() => {
                  setEmail(a.email);
                  setPassword("atlaslens2026");
                }}
                className="text-left text-sm px-2 py-1.5 rounded hover:bg-slate-100"
              >
                <span className="text-slate-700">{a.label}</span>
                <span className="block text-xs text-slate-400">{a.email}</span>
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-2">
            初期パスワード: <code className="bg-slate-100 px-1 rounded">atlaslens2026</code>
          </p>
        </div>
      </div>
    </div>
  );
}
