"use client";
import { useEffect, useRef, useState } from "react";
import type { PipelineRun } from "@/lib/api";
import {
  type PipelineStatusMessage,
  createPipelineSocket,
} from "@/lib/websocket";

export type PipelineStatus = {
  connected: boolean;
  activeRun: PipelineRun | null;
  recentRuns: PipelineRun[];
  liveOutput: string[];
  isRunning: boolean;
};

export function usePipelineStatus(): PipelineStatus {
  const [connected, setConnected] = useState(false);
  const [activeRun, setActiveRun] = useState<PipelineRun | null>(null);
  const [recentRuns, setRecentRuns] = useState<PipelineRun[]>([]);
  const [liveOutput, setLiveOutput] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = createPipelineSocket((msg: PipelineStatusMessage) => {
      if (msg.type === "pipeline_status") {
        setConnected(true);
        setActiveRun(msg.active_run);
        setRecentRuns(msg.recent_runs);
        setLiveOutput(msg.live_output ?? []);
      }
    }, () => {
      setConnected(false);
    });
    wsRef.current = ws;

    return () => {
      wsRef.current?.close();
    };
  }, []);

  return {
    connected,
    activeRun,
    recentRuns,
    liveOutput,
    isRunning: activeRun !== null,
  };
}
