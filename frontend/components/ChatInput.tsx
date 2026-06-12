"use client";

import { useState, useRef, useCallback } from "react";
import { Send, Paperclip, Loader2 } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export function ChatInput({ onSend, isLoading, disabled }: ChatInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [input, isLoading, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
  };

  return (
    <div className="flex items-end gap-2 p-4 border-t border-gray-800 bg-gray-950">
      <div className="flex-1 flex items-end gap-2 bg-gray-800 border border-gray-700 rounded-2xl px-4 py-2.5
                      focus-within:border-gorilla-500 transition-colors">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="メッセージを入力... (Shift+Enter で改行)"
          rows={1}
          className="flex-1 bg-transparent text-gray-100 placeholder:text-gray-500 text-sm
                     resize-none outline-none leading-relaxed max-h-[200px] py-0.5"
          disabled={disabled || isLoading}
        />
      </div>

      <button
        onClick={handleSend}
        disabled={!input.trim() || isLoading || disabled}
        className="flex-shrink-0 w-10 h-10 bg-gorilla-600 hover:bg-gorilla-500 disabled:bg-gray-700
                   disabled:cursor-not-allowed text-white rounded-xl flex items-center justify-center
                   transition-colors"
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Send className="w-4 h-4" />
        )}
      </button>
    </div>
  );
}
