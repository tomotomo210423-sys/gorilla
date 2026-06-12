"use client";

import { useEffect, useState } from "react";
import { Brain, RefreshCw, Filter, Trash2 } from "lucide-react";
import { Sidebar, SidebarToggle } from "@/components/Sidebar";
import { fetchMemories } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { clsx } from "clsx";

interface MemoryEntry {
  id: string;
  memory_type: string;
  content: string;
  importance_score: number;
  retention_score: number;
  access_count: number;
  tags: string[];
  topic: string | null;
  created_at: string;
}

const MEMORY_TYPES = [
  { value: "", label: "すべて" },
  { value: "short_term", label: "短期記憶" },
  { value: "long_term", label: "長期記憶" },
  { value: "semantic", label: "意味記憶" },
  { value: "episodic", label: "エピソード記憶" },
];

const MEMORY_TYPE_COLORS: Record<string, string> = {
  short_term: "bg-blue-900 text-blue-300",
  long_term: "bg-purple-900 text-purple-300",
  semantic: "bg-green-900 text-green-300",
  episodic: "bg-amber-900 text-amber-300",
};

export default function MemoryPage() {
  const { userId } = useAppStore();
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadMemories = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMemories(userId, filter || undefined);
      setMemories(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch memories");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMemories();
  }, [userId, filter]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <SidebarToggle />
          <Brain className="w-5 h-5 text-gorilla-400" />
          <h1 className="font-medium text-gray-100">記憶ビューア</h1>
          <button onClick={loadMemories} className="ml-auto btn-ghost p-2">
            <RefreshCw className={clsx("w-4 h-4", loading && "animate-spin")} />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-4">
          {/* Filter */}
          <div className="flex gap-2 mb-4 flex-wrap">
            {MEMORY_TYPES.map((t) => (
              <button
                key={t.value}
                onClick={() => setFilter(t.value)}
                className={clsx(
                  "px-3 py-1.5 rounded-full text-xs font-medium transition-colors",
                  filter === t.value
                    ? "bg-gorilla-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:text-gray-200"
                )}
              >
                {t.label}
              </button>
            ))}
          </div>

          {error && (
            <div className="p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm mb-4">
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="w-6 h-6 text-gray-500 animate-spin" />
            </div>
          ) : memories.length === 0 ? (
            <div className="text-center py-16 text-gray-500">
              <Brain className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>記憶がまだありません</p>
              <p className="text-sm mt-1">会話を続けると記憶が蓄積されます</p>
            </div>
          ) : (
            <div className="grid gap-3 max-w-4xl mx-auto">
              {memories.map((mem) => (
                <div
                  key={mem.id}
                  className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-700 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={clsx(
                          "text-xs px-2 py-0.5 rounded-full font-medium",
                          MEMORY_TYPE_COLORS[mem.memory_type] ?? "bg-gray-800 text-gray-400"
                        )}
                      >
                        {MEMORY_TYPES.find((t) => t.value === mem.memory_type)?.label ?? mem.memory_type}
                      </span>
                      {mem.topic && (
                        <span className="text-xs text-gray-500">{mem.topic}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-600 flex-shrink-0">
                      <span title="重要度">重要度: {(mem.importance_score * 100).toFixed(0)}%</span>
                      <span title="定着度">定着度: {(mem.retention_score * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  <p className="text-sm text-gray-300 leading-relaxed">{mem.content}</p>

                  {mem.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {mem.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-xs bg-gray-800 text-gray-500 px-2 py-0.5 rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-800">
                    <span className="text-xs text-gray-600">
                      {new Date(mem.created_at).toLocaleDateString("ja-JP")} ·
                      アクセス {mem.access_count}回
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
