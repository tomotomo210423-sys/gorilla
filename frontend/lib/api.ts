const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function sendMessageStream(params: {
  conversationId: string;
  userId: string;
  message: string;
  characterId?: string;
  temperature?: number;
  onChunk: (chunk: string) => void;
  onDone: () => void;
  onError: (error: string) => void;
}) {
  const response = await fetch(`${API_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversation_id: params.conversationId,
      user_id: params.userId,
      message: params.message,
      character_id: params.characterId,
      temperature: params.temperature ?? 0.8,
      stream: true,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    params.onError(error);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    params.onError("Stream not available");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = line.slice(6).trim();
        if (!data) continue;

        try {
          const parsed = JSON.parse(data);
          if (parsed.type === "content") {
            params.onChunk(parsed.content);
          } else if (parsed.type === "done") {
            params.onDone();
          } else if (parsed.type === "error") {
            params.onError(parsed.content);
          }
        } catch {
          // Ignore malformed JSON
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function fetchCharacters() {
  const res = await fetch(`${API_URL}/api/characters`);
  if (!res.ok) throw new Error("Failed to fetch characters");
  return res.json();
}

export async function createCharacter(data: Record<string, unknown>) {
  const res = await fetch(`${API_URL}/api/characters`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create character");
  return res.json();
}

export async function fetchMemories(userId: string, memoryType?: string) {
  const url = new URL(`${API_URL}/api/memory/${userId}`);
  if (memoryType) url.searchParams.set("memory_type", memoryType);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error("Failed to fetch memories");
  return res.json();
}

export async function ingestDocument(params: {
  userId: string;
  content: string;
  source: string;
}) {
  const res = await fetch(`${API_URL}/api/knowledge/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: params.userId,
      content: params.content,
      source: params.source,
    }),
  });
  if (!res.ok) throw new Error("Failed to ingest document");
  return res.json();
}

export async function checkHealth() {
  try {
    const res = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(3000) });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}
