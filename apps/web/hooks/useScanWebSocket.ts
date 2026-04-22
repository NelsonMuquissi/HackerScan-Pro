import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuthStore } from '@/store/useAuthStore';

interface UseScanWebSocketOptions {
  scanId?: string;
  onMessage?: (message: any) => void;
}

export function useScanWebSocket({ scanId, onMessage }: UseScanWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const token = useAuthStore((state) => state.token);

  const connect = useCallback(() => {
    if (!token) return;

    // Determine the WS URL (relative to current origin, but assuming the API is on 8000 in dev)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NEXT_PUBLIC_API_URL 
      ? new URL(process.env.NEXT_PUBLIC_API_URL).host 
      : 'localhost:8000';
    
    // Using the generic notifications endpoint
    const wsUrl = `${protocol}//${host}/ws/notifications/?token=${token}`;

    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      setIsConnected(true);
      console.log('Connected to notification WebSocket');
    };

    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // If scanId is provided, filter for that specific scan.
        // Backend sends payload.scan_id (not payload.id).
        if (scanId && data.type === 'scan_update') {
          if (data.payload?.scan_id === scanId) {
            onMessage?.(data.payload);
          }
        } else {
          // Otherwise pass the whole message
          onMessage?.(data);
        }
      } catch (e) {
        console.error('Error parsing WebSocket message', e);
      }
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };

    wsRef.current.onclose = () => {
      setIsConnected(false);
      console.log('Notification WebSocket closed');
    };
  }, [scanId, onMessage, token]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  return { isConnected, connect, disconnect };
}
