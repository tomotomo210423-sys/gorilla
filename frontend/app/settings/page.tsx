"use client";

import { useState, useEffect } from "react";
import { Settings, Save, Check, Cpu, Server, AlertTriangle } from "lucide-react";
import { Sidebar, SidebarToggle } from "@/components/Sidebar";
import { getConfig, saveConfig, WEB_LLM_MODELS, type AppMode } from "@/lib/config";
import { checkHealth } from "@/lib/api";
import { isWebGPUSupported } from "@/lib/webllm";
import { clsx } from "clsx";

export default function SettingsPage() {
  const [mode, setMode] = useState<AppMode>("browser");
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000");
  const [webllmModel, setWebllmModel] = useState(WEB_LLM_MODELS[0].id);
  const [saved, setSaved] = useState(false);
  const [healthStatus, setHealthStatus] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const webgpu = typeof window !== "undefined" ? isWebGPUSupported() : false;

  useEffect(() => {
    const cfg = getConfig();
    setMode(cfg.mode);
    setBackendUrl(cfg.backendUrl);
    setWebllmModel(cfg.webllmModel);
  }, []);

  const handleSave = () => {
    saveConfig({ mode, backendUrl, webllmModel });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const testConnection = async () => {
    setTesting(true);
    setHealthStatus(null);
    try {
      const originalUrl = getConfig().backendUrl;
      saveConfig({ backendUrl });
      const health = await checkHealth();
      saveConfig({ backendUrl: originalUrl });
      setHealthStatus(health ? `接続成功: ${health.model}` : "接続失敗: バックエンドが応答しません");
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <SidebarToggle />
          <Settings className="w-5 h-5 text-gorilla-400" />
          <h1 className="font-medium text-gray-100">設定</h1>
        </header>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="max-w-xl mx-auto space-y-6">

            {/* Mode selector */}
            <section className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-300">動作モード</h2>

              {/* Browser mode */}
              <label
                className={clsx(
                  "flex gap-3 p-4 border rounded-xl cursor-pointer transition-colors",
                  mode === "browser"
                    ? "border-gorilla-500 bg-gorilla-900/20"
                    : "border-gray-800 hover:border-gray-700"
                )}
              >
                <input
                  type="radio"
                  className="mt-1 accent-gorilla-500"
                  checked={mode === "browser"}
                  onChange={() => setMode("browser")}
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-purple-400" />
                    <span className="font-medium text-gray-100">ブラウザモード</span>
                    <span className="text-xs bg-purple-900/50 text-purple-400 px-2 py-0.5 rounded-full">
                      インストール不要
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    WebGPU を使ってブラウザ上でAIを動作させます。
                    初回のみモデルのダウンロードが必要です。
                  </p>
                  {!webgpu && (
                    <p className="flex items-center gap-1 text-xs text-amber-400 mt-2">
                      <AlertTriangle className="w-3 h-3" />
                      WebGPU 非対応ブラウザです。Chrome 113以上が必要です。
                    </p>
                  )}
                </div>
              </label>

              {/* Local backend mode */}
              <label
                className={clsx(
                  "flex gap-3 p-4 border rounded-xl cursor-pointer transition-colors",
                  mode === "local"
                    ? "border-gorilla-500 bg-gorilla-900/20"
                    : "border-gray-800 hover:border-gray-700"
                )}
              >
                <input
                  type="radio"
                  className="mt-1 accent-gorilla-500"
                  checked={mode === "local"}
                  onChange={() => setMode("local")}
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Server className="w-4 h-4 text-green-400" />
                    <span className="font-medium text-gray-100">ローカルバックエンド</span>
                    <span className="text-xs bg-green-900/50 text-green-400 px-2 py-0.5 rounded-full">
                      フル機能
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    Docker でバックエンドを起動して接続します。
                    記憶・RAG・キャラクターの全機能が使えます。
                  </p>
                </div>
              </label>
            </section>

            {/* Browser mode options */}
            {mode === "browser" && (
              <section className="space-y-3">
                <h2 className="text-sm font-semibold text-gray-300">ブラウザモデル選択</h2>
                <div className="space-y-2">
                  {WEB_LLM_MODELS.map((m) => (
                    <label
                      key={m.id}
                      className={clsx(
                        "flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors",
                        webllmModel === m.id
                          ? "border-gorilla-500 bg-gorilla-900/10"
                          : "border-gray-800 hover:border-gray-700"
                      )}
                    >
                      <input
                        type="radio"
                        className="accent-gorilla-500"
                        checked={webllmModel === m.id}
                        onChange={() => setWebllmModel(m.id)}
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-gray-200">{m.label}</span>
                          <span className="text-xs text-gray-500">{m.size}</span>
                        </div>
                        <span className="text-xs text-gray-500">{m.note}</span>
                      </div>
                    </label>
                  ))}
                </div>
              </section>
            )}

            {/* Backend URL */}
            {mode === "local" && (
              <section className="space-y-3">
                <h2 className="text-sm font-semibold text-gray-300">バックエンドURL</h2>
                <div className="flex gap-2">
                  <input
                    value={backendUrl}
                    onChange={(e) => setBackendUrl(e.target.value)}
                    placeholder="http://localhost:8000"
                    className="input-field flex-1"
                  />
                  <button
                    onClick={testConnection}
                    disabled={testing}
                    className="btn-ghost border border-gray-700 px-3"
                  >
                    {testing ? "確認中..." : "接続確認"}
                  </button>
                </div>
                {healthStatus && (
                  <p
                    className={clsx(
                      "text-sm",
                      healthStatus.includes("成功") ? "text-green-400" : "text-red-400"
                    )}
                  >
                    {healthStatus}
                  </p>
                )}
                <p className="text-xs text-gray-600">
                  ローカルで Docker を起動する場合: <code className="text-gray-400">./scripts/setup.sh</code>
                </p>
              </section>
            )}

            <button
              onClick={handleSave}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {saved ? (
                <>
                  <Check className="w-4 h-4" />
                  保存しました
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  設定を保存
                </>
              )}
            </button>

          </div>
        </div>
      </main>
    </div>
  );
}
