/**
 * WebLLM: Qwen2.5 runs directly in the browser via WebGPU.
 * Loaded from CDN at runtime — no npm bundle, no build-time issues.
 */

import type { WebLLMModel } from "./config";

// ── Inline types (CDN import has no TS types) ───────────────────────────────

interface InitProgress {
  progress: number;
  text: string;
}

interface CompletionChunk {
  choices: { delta: { content?: string } }[];
}

interface ChatEngine {
  chat: {
    completions: {
      create(params: {
        messages: { role: string; content: string }[];
        stream: true;
        temperature?: number;
        max_tokens?: number;
      }): Promise<AsyncIterable<CompletionChunk>>;
    };
  };
}

interface WebLLMModule {
  CreateMLCEngine(
    modelId: string,
    options?: { initProgressCallback?: (p: InitProgress) => void }
  ): Promise<ChatEngine>;
}

// ── Status types ─────────────────────────────────────────────────────────────

export type LoadingStatus =
  | { phase: "idle" }
  | { phase: "checking" }
  | { phase: "loading"; progress: number; text: string }
  | { phase: "ready"; model: string }
  | { phase: "error"; message: string };

// ── Module state ─────────────────────────────────────────────────────────────

let engineInstance: ChatEngine | null = null;
let loadedModel: string | null = null;
const CDN = "https://esm.run/@mlc-ai/web-llm";

// ── Public API ────────────────────────────────────────────────────────────────

export function isWebGPUSupported(): boolean {
  return typeof navigator !== "undefined" && "gpu" in navigator;
}

export async function loadWebLLM(
  modelId: WebLLMModel,
  onProgress: (s: LoadingStatus) => void
): Promise<boolean> {
  if (!isWebGPUSupported()) {
    onProgress({
      phase: "error",
      message: "WebGPU 非対応ブラウザです。Chrome 113 以上をお使いください。",
    });
    return false;
  }

  if (engineInstance && loadedModel === modelId) {
    onProgress({ phase: "ready", model: modelId });
    return true;
  }

  try {
    onProgress({ phase: "loading", progress: 0, text: "WebLLM を初期化中..." });

    // Dynamic CDN import — skipped by webpack, executed by browser
    const webllm = await import(
      /* webpackIgnore: true */
      CDN as string
    ) as unknown as WebLLMModule;

    engineInstance = await webllm.CreateMLCEngine(modelId, {
      initProgressCallback: (info) => {
        onProgress({
          phase: "loading",
          progress: Math.round(info.progress * 100),
          text: info.text,
        });
      },
    });

    loadedModel = modelId;
    onProgress({ phase: "ready", model: modelId });
    return true;
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    onProgress({ phase: "error", message: `読み込みエラー: ${msg}` });
    engineInstance = null;
    loadedModel = null;
    return false;
  }
}

export async function* generateStream(
  messages: { role: string; content: string }[],
  options?: { temperature?: number; max_tokens?: number }
): AsyncGenerator<string> {
  if (!engineInstance) throw new Error("WebLLM not loaded");

  const stream = await engineInstance.chat.completions.create({
    messages,
    stream: true,
    temperature: options?.temperature ?? 0.8,
    max_tokens: options?.max_tokens ?? 1024,
  });

  for await (const chunk of stream) {
    const content = chunk.choices[0]?.delta?.content;
    if (content) yield content;
  }
}

export async function generateOnce(
  messages: { role: string; content: string }[],
  options?: { temperature?: number; max_tokens?: number }
): Promise<string> {
  const parts: string[] = [];
  for await (const chunk of generateStream(messages, options)) {
    parts.push(chunk);
  }
  return parts.join("");
}

export function getLoadedModel(): string | null {
  return loadedModel;
}

export function unload(): void {
  engineInstance = null;
  loadedModel = null;
}
