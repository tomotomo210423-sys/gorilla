/**
 * WebLLM wrapper: runs Qwen2.5 directly in the browser via WebGPU.
 * Model files are downloaded from mlc.ai CDN on first use, then cached.
 */

import type { WebLLMModel } from "./config";

export type LoadingStatus =
  | { phase: "idle" }
  | { phase: "checking" }
  | { phase: "loading"; progress: number; text: string }
  | { phase: "ready"; model: string }
  | { phase: "error"; message: string };

type ProgressCallback = (status: LoadingStatus) => void;

let engineInstance: unknown = null;
let loadedModel: string | null = null;

export function isWebGPUSupported(): boolean {
  return typeof navigator !== "undefined" && "gpu" in navigator;
}

export async function loadWebLLM(
  modelId: WebLLMModel,
  onProgress: ProgressCallback
): Promise<boolean> {
  if (!isWebGPUSupported()) {
    onProgress({ phase: "error", message: "WebGPU非対応ブラウザです。Chrome 113以上をお使いください。" });
    return false;
  }

  if (engineInstance && loadedModel === modelId) {
    onProgress({ phase: "ready", model: modelId });
    return true;
  }

  try {
    onProgress({ phase: "loading", progress: 0, text: "WebLLMを初期化中..." });

    // Dynamic import — browser only, not included in SSR bundle
    const webllm = await import("@mlc-ai/web-llm");

    engineInstance = await webllm.CreateMLCEngine(modelId, {
      initProgressCallback: (info: { progress: number; text: string }) => {
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

  const engine = engineInstance as {
    chat: {
      completions: {
        create: (params: unknown) => Promise<AsyncIterable<{ choices: { delta: { content?: string } }[] }>>;
      };
    };
  };

  const stream = await engine.chat.completions.create({
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
