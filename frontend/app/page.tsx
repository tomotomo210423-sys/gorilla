"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { Bot, Plus, Loader2, Download } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { Sidebar, SidebarToggle } from "@/components/Sidebar";
import { ConnectionStatus } from "@/components/ConnectionStatus";
import { sendMessageStream } from "@/lib/api";
import { getConfig } from "@/lib/config";
import {
  loadWebLLM,
  generateStream,
  getLoadedModel,
  type LoadingStatus,
} from "@/lib/webllm";
import { searchMemories, maybeConsolidate } from "@/lib/browser-memory";

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 p-8">
      <div className="w-16 h-16 bg-gorilla-600 rounded-2xl flex items-center justify-center">
        <Bot className="w-8 h-8 text-white" />
      </div>
      <div className="text-center">
        <h2 className="text-xl font-semibold text-gray-100 mb-2">Gorilla AIへようこそ</h2>
        <p className="text-gray-400 text-sm max-w-sm">
          記憶・ロールプレイ・知識検索を備えたAIアシスタント
        </p>
      </div>
      <button onClick={onNew} className="btn-primary flex items-center gap-2">
        <Plus className="w-4 h-4" />
        会話を始める
      </button>
    </div>
  );
}

// ─── WebLLM loading overlay ───────────────────────────────────────────────────

function WebLLMLoader({
  status,
  onLoad,
}: {
  status: LoadingStatus;
  onLoad: () => void;
}) {
  if (status.phase === "ready") return null;

  // Idle: show manual load button (don't auto-download)
  if (status.phase === "idle") {
    return (
      <div className="absolute inset-0 bg-gray-950/80 backdrop-blur-sm z-10
                      flex flex-col items-center justify-center gap-4 p-8">
        <div className="w-14 h-14 bg-purple-700 rounded-2xl flex items-center justify-center">
          <Download className="w-7 h-7 text-white" />
        </div>
        <p className="text-gray-100 font-semibold text-lg">AIモデルの読み込み</p>
        <p className="text-gray-400 text-sm text-center max-w-xs">
          ブラウザ上でAIを動作させるためにモデルをダウンロードします。
          初回のみ必要で、以降はキャッシュされます。
        </p>
        <button
          onClick={onLoad}
          className="btn-primary flex items-center gap-2 px-6 py-3"
        >
          <Download className="w-4 h-4" />
          AIを読み込む
        </button>
        <p className="text-gray-600 text-xs">
          設定でモデルサイズを変更できます（デフォルト: Qwen2.5 1.5B ≈ 900MB）
        </p>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 bg-gray-950/90 backdrop-blur-sm z-10
                    flex flex-col items-center justify-center gap-4 p-8">
      <div className="w-12 h-12 bg-purple-600 rounded-xl flex items-center justify-center">
        {status.phase === "error" ? (
          <span className="text-white text-xl">✕</span>
        ) : (
          <Loader2 className="w-6 h-6 text-white animate-spin" />
        )}
      </div>

      {status.phase === "checking" && (
        <p className="text-gray-300 text-sm">ブラウザを確認中...</p>
      )}

      {status.phase === "loading" && (
        <>
          <p className="text-gray-200 font-medium">モデルを読み込み中...</p>
          <div className="w-64 h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-purple-500 rounded-full transition-all duration-500"
              style={{ width: `${status.progress}%` }}
            />
          </div>
          <p className="text-gray-500 text-xs text-center max-w-xs">{status.text}</p>
          <p className="text-gray-600 text-xs">初回のみダウンロードが必要です（キャッシュされます）</p>
        </>
      )}

      {status.phase === "error" && (
        <>
          <p className="text-red-400 font-medium">読み込みエラー</p>
          <p className="text-gray-500 text-sm text-center max-w-xs">{status.message}</p>
          <button onClick={onLoad} className="btn-ghost border border-gray-700 px-4 py-2 text-sm">
            再試行
          </button>
        </>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const {
    userId,
    conversations,
    activeConversationId,
    activeCharacterId,
    createConversation,
    addMessage,
    updateMessage,
    finalizeStreamingMessage,
    setConversationTitle,
  } = useAppStore();

  const [isLoading, setIsLoading] = useState(false);
  const [llmStatus, setLlmStatus] = useState<LoadingStatus>({ phase: "idle" });
  const [isBrowserMode, setIsBrowserMode] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  // Initialize on mount — do NOT auto-load the model; user must click explicitly
  useEffect(() => {
    const cfg = getConfig();
    if (cfg.mode === "browser") {
      setIsBrowserMode(true);
      if (getLoadedModel()) {
        setLlmStatus({ phase: "ready", model: getLoadedModel()! });
      }
      // phase stays "idle" → user sees the load button
    }
  }, []);

  const handleLoadModel = useCallback(() => {
    const cfg = getConfig();
    loadWebLLM(cfg.webllmModel, setLlmStatus);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeConversation?.messages.length]);

  // ── Browser mode send ───────────────────────────────────────────────────────
  const handleBrowserSend = useCallback(
    async (message: string, convId: string) => {
      const storeMessages = conversations.find((c) => c.id === convId)?.messages ?? [];
      const history = storeMessages.slice(-16).map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
      }));

      // Retrieve relevant memories
      const relevant = searchMemories(message);
      const memContext = relevant.length
        ? "\n\n【記憶から】\n" + relevant.map((m) => `- ${m.content}`).join("\n")
        : "";

      const systemPrompt =
        "あなたは親切なAIアシスタントです。" +
        "ユーザーの質問に対して正確で丁寧な回答を提供してください。" +
        memContext;

      const messages = [
        { role: "system" as const, content: systemPrompt },
        ...history,
        { role: "user" as const, content: message },
      ];

      const aiMsgId = addMessage(convId, {
        role: "assistant",
        content: "",
        isStreaming: true,
      });

      let fullContent = "";
      try {
        const cfg = getConfig();
        for await (const chunk of generateStream(messages, {
          temperature: 0.8,
          max_tokens: 1024,
        })) {
          fullContent += chunk;
          updateMessage(convId, aiMsgId, fullContent);
        }
        finalizeStreamingMessage(convId, aiMsgId);

        // Background memory consolidation
        const allMsgs = [
          ...history,
          { role: "user" as const, content: message },
          { role: "assistant" as const, content: fullContent },
        ];
        maybeConsolidate(allMsgs).catch(() => {});
      } catch (err) {
        const msg = err instanceof Error ? err.message : "エラーが発生しました";
        updateMessage(convId, aiMsgId, `エラー: ${msg}`);
        finalizeStreamingMessage(convId, aiMsgId);
      }
    },
    [conversations, addMessage, updateMessage, finalizeStreamingMessage]
  );

  // ── Backend mode send ───────────────────────────────────────────────────────
  const handleBackendSend = useCallback(
    async (message: string, convId: string) => {
      const aiMsgId = addMessage(convId, {
        role: "assistant",
        content: "",
        isStreaming: true,
      });

      let fullContent = "";
      try {
        await sendMessageStream({
          conversationId: convId,
          userId,
          message,
          characterId: activeCharacterId ?? undefined,
          onChunk: (chunk) => {
            fullContent += chunk;
            updateMessage(convId, aiMsgId, fullContent);
          },
          onDone: () => finalizeStreamingMessage(convId, aiMsgId),
          onError: (err) => {
            updateMessage(convId, aiMsgId, `エラー: ${err}`);
            finalizeStreamingMessage(convId, aiMsgId);
          },
        });
      } catch (err) {
        let msg = "エラーが発生しました";
        if (err instanceof TypeError && err.message.toLowerCase().includes("fetch")) {
          msg = "バックエンドに接続できません。Dockerが起動しているか確認してください。";
        } else if (err instanceof Error) {
          msg = err.message;
        }
        updateMessage(convId, aiMsgId, `エラー: ${msg}`);
        finalizeStreamingMessage(convId, aiMsgId);
      }
    },
    [userId, activeCharacterId, addMessage, updateMessage, finalizeStreamingMessage]
  );

  // ── Unified send ─────────────────────────────────────────────────────────────
  const handleSend = useCallback(
    async (message: string) => {
      setIsLoading(true);
      let convId = activeConversationId;
      if (!convId) convId = createConversation();

      addMessage(convId, { role: "user", content: message });

      // Auto-title
      if (
        conversations.find((c) => c.id === convId)?.title === "新しい会話" &&
        message.length > 0
      ) {
        setConversationTitle(convId, message.slice(0, 30) + (message.length > 30 ? "..." : ""));
      }

      try {
        if (isBrowserMode) {
          await handleBrowserSend(message, convId);
        } else {
          await handleBackendSend(message, convId);
        }
      } finally {
        setIsLoading(false);
      }
    },
    [
      activeConversationId,
      conversations,
      isBrowserMode,
      createConversation,
      addMessage,
      setConversationTitle,
      handleBrowserSend,
      handleBackendSend,
    ]
  );

  // Only allow sending when model is actually ready (or not in browser mode)
  const isReady = !isBrowserMode || llmStatus.phase === "ready";

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />

      <main className="flex-1 flex flex-col min-w-0 relative">
        {/* WebLLM loading overlay */}
        {isBrowserMode && <WebLLMLoader status={llmStatus} onLoad={handleLoadModel} />}

        {/* Header */}
        <header className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <SidebarToggle />
          <h1 className="font-medium text-gray-100 truncate">
            {activeConversation?.title ?? "Gorilla AI"}
          </h1>
          <div className="ml-auto">
            <ConnectionStatus />
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {!activeConversation || activeConversation.messages.length === 0 ? (
            <EmptyState onNew={() => createConversation()} />
          ) : (
            <div className="p-4 space-y-6 max-w-4xl mx-auto">
              {activeConversation.messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <ChatInput
          onSend={handleSend}
          isLoading={isLoading}
          disabled={!isReady || llmStatus.phase === "error"}
        />
      </main>
    </div>
  );
}
