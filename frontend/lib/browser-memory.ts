/**
 * In-browser memory using localStorage.
 * Simplified version of the 4-layer memory for browser-only mode.
 */

import { generateOnce } from "./webllm";

const MEMORY_KEY = "gorilla-memories";
const MAX_MEMORIES = 50;

export interface BrowserMemory {
  id: string;
  content: string;
  tags: string[];
  importance: number;
  createdAt: number;
}

export function loadMemories(): BrowserMemory[] {
  try {
    const raw = localStorage.getItem(MEMORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveMemories(memories: BrowserMemory[]): void {
  localStorage.setItem(MEMORY_KEY, JSON.stringify(memories.slice(0, MAX_MEMORIES)));
}

export function addMemory(content: string, tags: string[] = [], importance = 0.5): void {
  const memories = loadMemories();
  memories.unshift({
    id: crypto.randomUUID(),
    content,
    tags,
    importance,
    createdAt: Date.now(),
  });
  saveMemories(memories);
}

export function searchMemories(query: string, topK = 3): BrowserMemory[] {
  const memories = loadMemories();
  const queryWords = query.toLowerCase().split(/\s+/);

  const scored = memories.map((m) => {
    const text = (m.content + " " + m.tags.join(" ")).toLowerCase();
    const score = queryWords.filter((w) => text.includes(w)).length / queryWords.length;
    return { m, score };
  });

  return scored
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score || b.m.importance - a.m.importance)
    .slice(0, topK)
    .map(({ m }) => m);
}

export async function maybeConsolidate(
  messages: { role: string; content: string }[]
): Promise<void> {
  if (messages.length < 10) return;

  const text = messages
    .slice(-10)
    .map((m) => `${m.role}: ${m.content}`)
    .join("\n");

  try {
    const summary = await generateOnce(
      [
        {
          role: "system",
          content: "会話から重要な情報を1〜2文で要約してください。重要でない場合は「なし」と答えてください。",
        },
        { role: "user", content: text },
      ],
      { temperature: 0.2, max_tokens: 128 }
    );

    if (!summary.includes("なし") && summary.length > 10) {
      addMemory(summary, [], 0.7);
    }
  } catch {
    // Memory consolidation is best-effort
  }
}
