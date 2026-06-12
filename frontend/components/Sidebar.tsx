"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  Brain,
  Users,
  BookOpen,
  Plus,
  Settings,
  Menu,
  X,
  Trash2,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { clsx } from "clsx";

const navItems = [
  { href: "/", icon: MessageSquare, label: "チャット" },
  { href: "/memory", icon: Brain, label: "記憶" },
  { href: "/character", icon: Users, label: "キャラクター" },
  { href: "/knowledge", icon: BookOpen, label: "知識ベース" },
];

export function Sidebar() {
  const pathname = usePathname();
  const {
    conversations,
    activeConversationId,
    sidebarOpen,
    toggleSidebar,
    createConversation,
    setActiveConversation,
    deleteConversation,
  } = useAppStore();

  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={toggleSidebar}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          "fixed top-0 left-0 h-full w-64 bg-gray-900 border-r border-gray-800 z-30",
          "flex flex-col transition-transform duration-300",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
          "lg:relative lg:translate-x-0 lg:z-auto"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gorilla-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">G</span>
            </div>
            <span className="font-semibold text-gray-100">Gorilla AI</span>
          </div>
          <button onClick={toggleSidebar} className="btn-ghost lg:hidden p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-3 border-b border-gray-800">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "sidebar-item",
                pathname === item.href && "active"
              )}
            >
              <item.icon className="w-4 h-4 flex-shrink-0" />
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Conversations */}
        <div className="flex-1 overflow-y-auto p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">
              会話履歴
            </span>
            <button
              onClick={() => createConversation()}
              className="btn-ghost p-1 text-gorilla-400"
              title="新しい会話"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-1">
            {conversations.length === 0 ? (
              <p className="text-xs text-gray-600 py-2 text-center">
                会話履歴なし
              </p>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={clsx(
                    "group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer",
                    "text-sm transition-colors",
                    activeConversationId === conv.id
                      ? "bg-gray-800 text-gray-100"
                      : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                  )}
                  onClick={() => setActiveConversation(conv.id)}
                >
                  <span className="flex-1 truncate">{conv.title}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteConversation(conv.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 text-gray-600
                               hover:text-red-400 transition-all p-0.5"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-gray-800">
          <Link href="/settings" className="sidebar-item">
            <Settings className="w-4 h-4" />
            設定
          </Link>
        </div>
      </aside>
    </>
  );
}

export function SidebarToggle() {
  const { toggleSidebar } = useAppStore();
  return (
    <button onClick={toggleSidebar} className="btn-ghost p-2 lg:hidden">
      <Menu className="w-5 h-5" />
    </button>
  );
}
