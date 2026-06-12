import { create } from "zustand";
import { persist } from "zustand/middleware";
import { v4 as uuidv4 } from "uuid";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  reasoningTrace?: string;
}

export interface Conversation {
  id: string;
  title: string;
  characterId?: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

export interface Character {
  id: string;
  name: string;
  description: string;
  personality: Record<string, number>;
  speechStyle: Record<string, unknown>;
  emotionBaseline: Record<string, number>;
}

interface AppState {
  userId: string;
  conversations: Conversation[];
  activeConversationId: string | null;
  characters: Character[];
  activeCharacterId: string | null;
  sidebarOpen: boolean;

  // Actions
  setUserId: (id: string) => void;
  createConversation: () => string;
  setActiveConversation: (id: string) => void;
  addMessage: (conversationId: string, message: Omit<Message, "id" | "timestamp">) => string;
  updateMessage: (conversationId: string, messageId: string, content: string) => void;
  finalizeStreamingMessage: (conversationId: string, messageId: string) => void;
  setConversationTitle: (conversationId: string, title: string) => void;
  deleteConversation: (id: string) => void;
  setCharacters: (chars: Character[]) => void;
  setActiveCharacter: (id: string | null) => void;
  toggleSidebar: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      userId: uuidv4(),
      conversations: [],
      activeConversationId: null,
      characters: [],
      activeCharacterId: null,
      sidebarOpen: true,

      setUserId: (id) => set({ userId: id }),

      createConversation: () => {
        const id = uuidv4();
        const conv: Conversation = {
          id,
          title: "新しい会話",
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
          characterId: get().activeCharacterId ?? undefined,
        };
        set((s) => ({
          conversations: [conv, ...s.conversations],
          activeConversationId: id,
        }));
        return id;
      },

      setActiveConversation: (id) => set({ activeConversationId: id }),

      addMessage: (conversationId, message) => {
        const id = uuidv4();
        const fullMessage: Message = { ...message, id, timestamp: new Date() };
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? { ...c, messages: [...c.messages, fullMessage], updatedAt: new Date() }
              : c
          ),
        }));
        return id;
      },

      updateMessage: (conversationId, messageId, content) => {
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === messageId ? { ...m, content } : m
                  ),
                }
              : c
          ),
        }));
      },

      finalizeStreamingMessage: (conversationId, messageId) => {
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === messageId ? { ...m, isStreaming: false } : m
                  ),
                }
              : c
          ),
        }));
      },

      setConversationTitle: (conversationId, title) => {
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId ? { ...c, title } : c
          ),
        }));
      },

      deleteConversation: (id) => {
        set((s) => {
          const remaining = s.conversations.filter((c) => c.id !== id);
          return {
            conversations: remaining,
            activeConversationId:
              s.activeConversationId === id
                ? (remaining[0]?.id ?? null)
                : s.activeConversationId,
          };
        });
      },

      setCharacters: (chars) => set({ characters: chars }),
      setActiveCharacter: (id) => set({ activeCharacterId: id }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
    }),
    {
      name: "gorilla-ai-store",
      partialize: (s) => ({
        userId: s.userId,
        conversations: s.conversations,
        activeConversationId: s.activeConversationId,
        activeCharacterId: s.activeCharacterId,
      }),
    }
  )
);
