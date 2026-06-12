"use client";

import { useEffect, useState } from "react";
import { Wifi, WifiOff, Cpu, AlertCircle, X } from "lucide-react";
import Link from "next/link";
import { getConfig } from "@/lib/config";
import { checkHealth } from "@/lib/api";
import { isWebGPUSupported } from "@/lib/webllm";

type Status = "checking" | "connected" | "disconnected" | "browser";

export function ConnectionStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [model, setModel] = useState("");
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const cfg = getConfig();

    if (cfg.mode === "browser") {
      setStatus("browser");
      setModel(cfg.webllmModel.replace("-q4f16_1-MLC", "").replace("Instruct", "Instruct "));
      return;
    }

    checkHealth().then((health) => {
      if (health) {
        setStatus("connected");
        setModel(health.model);
      } else {
        setStatus("disconnected");
      }
    });
  }, []);

  if (dismissed || status === "checking") return null;

  if (status === "connected") {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 bg-green-900/30 border border-green-700/50
                      rounded-full text-xs text-green-400">
        <Wifi className="w-3 h-3" />
        <span>{model}</span>
      </div>
    );
  }

  if (status === "browser") {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 bg-purple-900/30 border border-purple-700/50
                      rounded-full text-xs text-purple-400">
        <Cpu className="w-3 h-3" />
        <span>ブラウザモード</span>
      </div>
    );
  }

  // Disconnected
  if (dismissed) return null;
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-900/30 border border-amber-700/50
                    rounded-lg text-xs text-amber-400">
      <WifiOff className="w-3 h-3 flex-shrink-0" />
      <span>バックエンド未接続 —</span>
      <Link href="/settings/" className="underline hover:no-underline">
        設定
      </Link>
      <button onClick={() => setDismissed(true)} className="ml-1 hover:text-amber-200">
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}
