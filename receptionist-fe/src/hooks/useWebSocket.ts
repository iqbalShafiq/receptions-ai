import { useEffect, useRef, useState } from 'react';
import { useConversationStore } from '../store/conversationStore';
import type { VoiceMessage, VoiceResponse } from '../types/api';

interface UseWebSocketOptions {
  url: string;
  onMessage?: (data: VoiceResponse) => void;
  onError?: (error: string) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export const useWebSocket = ({
  url,
  onMessage,
  onError,
  onConnect,
  onDisconnect,
}: UseWebSocketOptions) => {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const { conversationId, setConnected, setError } = useConversationStore();

  useEffect(() => {
    const connect = () => {
      try {
        const wsUrl = `${url}?conversation_id=${conversationId}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          setIsConnected(true);
          setConnected(true);
          onConnect?.();
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as VoiceResponse;
            onMessage?.(data);
          } catch (e) {
            // Silent fail for unparseable messages
          }
        };

        ws.onerror = (event) => {
          const errorMsg = `WebSocket error`;
          setError(errorMsg);
          onError?.(errorMsg);
        };

        ws.onclose = (event: CloseEvent) => {
          setIsConnected(false);
          setConnected(false);
          onDisconnect?.();
        };

        wsRef.current = ws;
      } catch (e) {
        const errorMsg = `WebSocket error: ${String(e)}`;
        setError(errorMsg);
        onError?.(errorMsg);
      }
    };

    connect();

    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, [url, conversationId]);

  const send = (message: VoiceMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  };

  return { isConnected, send, ws: wsRef.current };
};
