"use client";

import { useEffect, useRef, useCallback } from "react";
import { Bot, Plus, AlertCircle } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { Sidebar, SidebarToggle } from "@/components/Sidebar";
import { sendMessageStream } from "@/lib/api";
import { useState } from "react";

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 p-8">
      <div className="w-16 h-16 bg-gorilla-600 rounded-2xl flex items-center justify-center">
        <Bot className="w-8 h-8 text-white" />
      </div>
      <div className="text-center">
        <h2 className="text-xl font-semibold text-gray-100 mb-2">Gorilla AIへようこそ</h2>
        <p className="text-gray-400 text-sm max-w-sm">
          高度な記憶システムとロールプレイ機能を持つAIアシスタント
        </p>
      </div>
      <button onClick={onNew} className="btn-primary flex items-center gap-2">
        <Plus className="w-4 h-4" />
        新しい会話を始める
      </button>
    </div>
  );
}

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
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeConversation?.messages.length, isLoading]);

  const handleSend = useCallback(
    async (message: string) => {
      setError(null);

      let convId = activeConversationId;
      if (!convId) {
        convId = createConversation();
      }

      addMessage(convId, { role: "user", content: message });

      const aiMsgId = addMessage(convId, {
        role: "assistant",
        content: "",
        isStreaming: true,
      });

      setIsLoading(true);
      let fullContent = "";

      try {
        await sendMessageStream({
          conversationId: convId,
          userId,
          message,
          characterId: activeCharacterId ?? undefined,
          onChunk: (chunk) => {
            fullContent += chunk;
            updateMessage(convId!, aiMsgId, fullContent);
          },
          onDone: () => {
            finalizeStreamingMessage(convId!, aiMsgId);

            // Auto-title from first message
            const conv = conversations.find((c) => c.id === convId);
            if (conv && conv.title === "新しい会話" && message.length > 0) {
              setConversationTitle(convId!, message.slice(0, 30) + (message.length > 30 ? "..." : ""));
            }
          },
          onError: (err) => {
            setError(err);
            updateMessage(convId!, aiMsgId, `エラー: ${err}`);
            finalizeStreamingMessage(convId!, aiMsgId);
          },
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        setError(msg);
        updateMessage(convId!, aiMsgId, `エラーが発生しました: ${msg}`);
        finalizeStreamingMessage(convId!, aiMsgId);
      } finally {
        setIsLoading(false);
      }
    },
    [
      activeConversationId,
      userId,
      activeCharacterId,
      conversations,
      createConversation,
      addMessage,
      updateMessage,
      finalizeStreamingMessage,
      setConversationTitle,
    ]
  );

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />

      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <SidebarToggle />
          <h1 className="font-medium text-gray-100 truncate">
            {activeConversation?.title ?? "Gorilla AI"}
          </h1>
          {error && (
            <div className="flex items-center gap-1.5 ml-auto text-red-400 text-xs">
              <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="truncate max-w-[200px]">API接続エラー</span>
            </div>
          )}
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
        <ChatInput onSend={handleSend} isLoading={isLoading} />
      </main>
    </div>
  );
}
