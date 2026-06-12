"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import type { Message } from "@/lib/store";

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const [showTrace, setShowTrace] = useState(false);
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 animate-slide-up ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
          ${isUser ? "bg-gorilla-600" : "bg-gray-700"}`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-gorilla-400" />
        )}
      </div>

      {/* Message */}
      <div className={`flex flex-col gap-1 max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
        <div className={isUser ? "message-user" : "message-assistant"}>
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
          ) : (
            <div className="prose-dark text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              {message.isStreaming && (
                <span className="inline-flex gap-1 ml-1">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </span>
              )}
            </div>
          )}
        </div>

        {/* Reasoning trace toggle */}
        {message.reasoningTrace && (
          <div className="w-full">
            <button
              onClick={() => setShowTrace(!showTrace)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-400 transition-colors"
            >
              {showTrace ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
              思考プロセスを{showTrace ? "隠す" : "表示"}
            </button>
            {showTrace && (
              <div className="mt-1 p-3 bg-gray-900 rounded-lg border border-gray-700 text-xs text-gray-400 whitespace-pre-wrap">
                {message.reasoningTrace}
              </div>
            )}
          </div>
        )}

        <span className="text-xs text-gray-600">
          {new Date(message.timestamp).toLocaleTimeString("ja-JP", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>
  );
}
