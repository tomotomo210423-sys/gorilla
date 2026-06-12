"use client";

import { useEffect, useState } from "react";
import { Users, Plus, Edit3, Trash2, Check, X } from "lucide-react";
import { Sidebar, SidebarToggle } from "@/components/Sidebar";
import { fetchCharacters, createCharacter } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { clsx } from "clsx";

interface CharacterData {
  id: string;
  name: string;
  description: string;
  personality: Record<string, number>;
  speech_style: Record<string, unknown>;
  emotion_baseline: Record<string, number>;
  created_at: string;
}

const PERSONALITY_LABELS: Record<string, string> = {
  openness: "開放性",
  conscientiousness: "誠実性",
  extraversion: "外向性",
  agreeableness: "協調性",
  neuroticism: "神経症傾向",
};

function CharacterCard({
  character,
  isActive,
  onSelect,
}: {
  character: CharacterData;
  isActive: boolean;
  onSelect: () => void;
}) {
  const dominantEmotion = Object.entries(character.emotion_baseline)
    .sort((a, b) => b[1] - a[1])[0];

  return (
    <div
      className={clsx(
        "bg-gray-900 border rounded-xl p-4 cursor-pointer transition-all",
        isActive ? "border-gorilla-500 shadow-lg shadow-gorilla-500/10" : "border-gray-800 hover:border-gray-700"
      )}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-gorilla-600 to-purple-600 rounded-full
                          flex items-center justify-center text-white font-bold">
            {character.name[0]}
          </div>
          <div>
            <h3 className="font-medium text-gray-100">{character.name}</h3>
            {dominantEmotion && (
              <span className="text-xs text-gray-500">
                主な感情: {dominantEmotion[0]}
              </span>
            )}
          </div>
        </div>
        {isActive && (
          <span className="bg-gorilla-600 text-white text-xs px-2 py-0.5 rounded-full">
            使用中
          </span>
        )}
      </div>

      <p className="text-sm text-gray-400 line-clamp-2 mb-3">{character.description}</p>

      {/* Personality bars */}
      <div className="space-y-1.5">
        {Object.entries(PERSONALITY_LABELS).map(([key, label]) => (
          <div key={key} className="flex items-center gap-2">
            <span className="text-xs text-gray-600 w-16">{label}</span>
            <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gorilla-600 rounded-full"
                style={{ width: `${(character.personality[key] ?? 0.5) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CreateCharacterModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({
    name: "",
    description: "",
    speech_tone: "friendly",
    world_setting: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!form.name || !form.description) return;
    setLoading(true);
    setError(null);
    try {
      await createCharacter({
        name: form.name,
        description: form.description,
        speech_style: { tone: form.speech_tone, formality: 0.5 },
        world_setting: form.world_setting || null,
      });
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-md">
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <h2 className="font-semibold text-gray-100">新しいキャラクターを作成</h2>
          <button onClick={onClose} className="btn-ghost p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">名前 *</label>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="例: アリス"
              className="input-field w-full"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">性格・説明 *</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="性格、特徴、振る舞いを詳しく記述してください..."
              rows={4}
              className="input-field w-full resize-none"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">口調</label>
            <select
              value={form.speech_tone}
              onChange={(e) => setForm({ ...form, speech_tone: e.target.value })}
              className="input-field w-full"
            >
              <option value="friendly">フレンドリー</option>
              <option value="formal">丁寧・フォーマル</option>
              <option value="casual">カジュアル</option>
              <option value="tsundere">ツンデレ</option>
              <option value="cool">クール</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">世界設定 (任意)</label>
            <textarea
              value={form.world_setting}
              onChange={(e) => setForm({ ...form, world_setting: e.target.value })}
              placeholder="ファンタジー世界、近未来など..."
              rows={2}
              className="input-field w-full resize-none"
            />
          </div>

          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}
        </div>

        <div className="flex gap-2 p-4 border-t border-gray-800">
          <button onClick={onClose} className="btn-ghost flex-1">キャンセル</button>
          <button
            onClick={handleCreate}
            disabled={!form.name || !form.description || loading}
            className="btn-primary flex-1"
          >
            {loading ? "作成中..." : "作成"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CharacterPage() {
  const { activeCharacterId, setActiveCharacter } = useAppStore();
  const [characters, setCharacters] = useState<CharacterData[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchCharacters();
      setCharacters(data);
    } catch {
      // API not available
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <SidebarToggle />
          <Users className="w-5 h-5 text-gorilla-400" />
          <h1 className="font-medium text-gray-100">キャラクター管理</h1>
          <button
            onClick={() => setShowCreate(true)}
            className="ml-auto btn-primary flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            新規作成
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-4">
          {/* No character option */}
          <div
            className={clsx(
              "mb-4 p-4 border rounded-xl cursor-pointer transition-all",
              !activeCharacterId
                ? "border-gorilla-500 bg-gorilla-900/20"
                : "border-gray-800 hover:border-gray-700"
            )}
            onClick={() => setActiveCharacter(null)}
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gray-700 rounded-full flex items-center justify-center">
                <Users className="w-5 h-5 text-gray-400" />
              </div>
              <div>
                <h3 className="font-medium text-gray-100">キャラクターなし</h3>
                <p className="text-sm text-gray-500">汎用AIアシスタントモード</p>
              </div>
              {!activeCharacterId && (
                <Check className="w-4 h-4 text-gorilla-400 ml-auto" />
              )}
            </div>
          </div>

          {loading ? (
            <div className="text-center py-16 text-gray-500">読み込み中...</div>
          ) : characters.length === 0 ? (
            <div className="text-center py-16 text-gray-500">
              <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>キャラクターがまだいません</p>
              <button onClick={() => setShowCreate(true)} className="btn-primary mt-4">
                最初のキャラクターを作成
              </button>
            </div>
          ) : (
            <div className="grid gap-3 max-w-4xl mx-auto sm:grid-cols-2">
              {characters.map((char) => (
                <CharacterCard
                  key={char.id}
                  character={char}
                  isActive={activeCharacterId === char.id}
                  onSelect={() => setActiveCharacter(char.id)}
                />
              ))}
            </div>
          )}
        </div>
      </main>

      {showCreate && (
        <CreateCharacterModal
          onClose={() => setShowCreate(false)}
          onCreated={load}
        />
      )}
    </div>
  );
}
