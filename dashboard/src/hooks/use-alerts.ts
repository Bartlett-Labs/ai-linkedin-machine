"use client";
import { useEffect, useRef, useState } from "react";
import { type AlertMessage, type AlertPayload, createAlertSocket } from "@/lib/websocket";

export function useAlerts() {
  const [alerts, setAlerts] = useState<AlertPayload[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    wsRef.current = createAlertSocket((msg: AlertMessage) => {
      if (msg.type === "alerts") setAlerts(msg.data);
    });
    return () => { wsRef.current?.close(); };
  }, []);

  return alerts;
}
