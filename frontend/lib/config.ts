/**
 * Runtime configuration stored in localStorage.
 * Allows users on GitHub Pages to configure their own backend URL.
 */

export type AppMode = "browser" | "local";
export type WebLLMModel =
  | "Qwen2.5-1.5B-Instruct-q4f16_1-MLC"
  | "Qwen2.5-3B-Instruct-q4f16_1-MLC"
  | "Qwen2.5-7B-Instruct-q4f16_1-MLC";

export interface AppConfig {
  mode: AppMode;
  backendUrl: string;
  webllmModel: WebLLMModel;
}

const DEFAULT_CONFIG: AppConfig = {
  mode: "browser",
  backendUrl: "http://localhost:8000",
  webllmModel: "Qwen2.5-1.5B-Instruct-q4f16_1-MLC",
};

const STORAGE_KEY = "gorilla-ai-config";

export function getConfig(): AppConfig {
  if (typeof window === "undefined") return DEFAULT_CONFIG;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_CONFIG;
    return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_CONFIG;
  }
}

export function saveConfig(config: Partial<AppConfig>): void {
  if (typeof window === "undefined") return;
  const current = getConfig();
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...current, ...config }));
}

export const WEB_LLM_MODELS: { id: WebLLMModel; label: string; size: string; note: string }[] = [
  {
    id: "Qwen2.5-1.5B-Instruct-q4f16_1-MLC",
    label: "Qwen2.5 1.5B",
    size: "~900MB",
    note: "高速・軽量（推奨）",
  },
  {
    id: "Qwen2.5-3B-Instruct-q4f16_1-MLC",
    label: "Qwen2.5 3B",
    size: "~1.8GB",
    note: "バランス型",
  },
  {
    id: "Qwen2.5-7B-Instruct-q4f16_1-MLC",
    label: "Qwen2.5 7B",
    size: "~4.2GB",
    note: "高品質（VRAM 6GB以上推奨）",
  },
];
