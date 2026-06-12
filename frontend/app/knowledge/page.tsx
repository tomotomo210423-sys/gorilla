"use client";

import { useState } from "react";
import { BookOpen, Upload, Search, Check, Loader2 } from "lucide-react";
import { Sidebar, SidebarToggle } from "@/components/Sidebar";
import { ingestDocument } from "@/lib/api";
import { useAppStore } from "@/lib/store";

export default function KnowledgePage() {
  const { userId } = useAppStore();
  const [mode, setMode] = useState<"text" | "file">("text");
  const [content, setContent] = useState("");
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ chunks: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleIngest = async () => {
    if (!content.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const data = await ingestDocument({ userId, content, source });
      setResult(data);
      setContent("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to ingest");
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const text = await file.text();
      const data = await ingestDocument({ userId, content: text, source: file.name });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload");
    } finally {
      setLoading(false);
      e.target.value = "";
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <SidebarToggle />
          <BookOpen className="w-5 h-5 text-gorilla-400" />
          <h1 className="font-medium text-gray-100">知識ベース管理</h1>
        </header>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="max-w-2xl mx-auto space-y-6">
            {/* Info */}
            <div className="p-4 bg-gorilla-900/20 border border-gorilla-700/50 rounded-xl text-sm text-gorilla-300">
              <p>テキストやファイルを取り込むと、AIがその知識を使って回答できるようになります。</p>
            </div>

            {/* Mode selector */}
            <div className="flex gap-2">
              <button
                onClick={() => setMode("text")}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors
                  ${mode === "text" ? "bg-gorilla-600 text-white" : "bg-gray-800 text-gray-400 hover:text-gray-200"}`}
              >
                テキスト入力
              </button>
              <button
                onClick={() => setMode("file")}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors
                  ${mode === "file" ? "bg-gorilla-600 text-white" : "bg-gray-800 text-gray-400 hover:text-gray-200"}`}
              >
                ファイルアップロード
              </button>
            </div>

            {mode === "text" ? (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">ソース名（任意）</label>
                  <input
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    placeholder="例: Wikipedia, マニュアル, etc."
                    className="input-field w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">コンテンツ</label>
                  <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="AIに学習させたいテキストを入力してください..."
                    rows={12}
                    className="input-field w-full resize-none"
                  />
                </div>
                <button
                  onClick={handleIngest}
                  disabled={!content.trim() || loading}
                  className="btn-primary w-full flex items-center justify-center gap-2"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BookOpen className="w-4 h-4" />}
                  {loading ? "処理中..." : "知識として取り込む"}
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <label
                  className="flex flex-col items-center justify-center w-full h-48 border-2 border-dashed
                               border-gray-700 rounded-xl cursor-pointer hover:border-gorilla-500 transition-colors"
                >
                  <Upload className="w-8 h-8 text-gray-500 mb-2" />
                  <span className="text-sm text-gray-500">クリックしてファイルを選択</span>
                  <span className="text-xs text-gray-600 mt-1">.txt, .md に対応</span>
                  <input
                    type="file"
                    accept=".txt,.md"
                    className="hidden"
                    onChange={handleFileUpload}
                    disabled={loading}
                  />
                </label>
                {loading && (
                  <div className="flex items-center justify-center gap-2 text-gray-400">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm">アップロード中...</span>
                  </div>
                )}
              </div>
            )}

            {/* Result */}
            {result && (
              <div className="flex items-center gap-2 p-3 bg-green-900/30 border border-green-700 rounded-lg">
                <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
                <span className="text-sm text-green-300">
                  {result.chunks} チャンクとして取り込み完了
                </span>
              </div>
            )}

            {error && (
              <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
                {error}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
