'use client';

import { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';
import { useAuthStore } from '@/store/useAuthStore';

interface TerminalOutputProps {
  scanId: string;
}

export function TerminalOutput({ scanId }: TerminalOutputProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  // Holds the xterm Terminal instance — disposed on unmount
  const xtermRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const isConnectedRef = useRef(false);

  // ── Mandatory xterm cleanup on unmount ──────────────────────────────────
  // Without this, xterm.js accumulates instances in memory on every remount.
  useEffect(() => {
    return () => {
      xtermRef.current?.dispose();
      xtermRef.current = null;
    };
  }, []);

  // ── Main effect: initialise terminal + open WebSocket ───────────────────
  useEffect(() => {
    if (!terminalRef.current) return;

    // 1. Boot xterm.js
    const term = new Terminal({
      theme: {
        background: '#050505',
        foreground: '#00ff00',
        cursor: '#00ff00',
        black: '#000000',
        red: '#ff003c',
        green: '#00ff00',
        yellow: '#ffcc00',
      },
      fontFamily: '"Fira Code", monospace',
      fontSize: 14,
      cursorBlink: true,
      disableStdin: true,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    // Safety: only fit if the terminal container has actual dimensions
    const safeFit = () => {
      if (terminalRef.current && terminalRef.current.offsetWidth > 0 && terminalRef.current.offsetHeight > 0) {
        try {
          fitAddon.fit();
        } catch (e) {
          console.warn('Terminal fit failed:', e);
        }
      }
    };
    
    // Initial fit with a tiny delay to ensure layout is ready
    setTimeout(safeFit, 50);

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    term.writeln('\x1b[1;32m[HackerScan] Initializing secure terminal interface...\x1b[0m');

    // 2. Build the WebSocket URL — append JWT as query param so Django's
    //    JWTAuthMiddleware can authenticate the WS handshake.
    const token = useAuthStore.getState().token;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const apiHost = process.env.NEXT_PUBLIC_API_URL
      ? new URL(process.env.NEXT_PUBLIC_API_URL).host
      : 'localhost:8000';
    const tokenParam = token ? `?token=${token}` : '';
    const wsUrl = `${protocol}//${apiHost}/ws/scans/${scanId}/${tokenParam}`;

    // 3. Open the real WebSocket
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      isConnectedRef.current = true;
      term.writeln(`\x1b[1;32m[SYSTEM] Connected to scan session ${scanId}\x1b[0m`);
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'log' && data.message) {
          // Format based on message content
          if (data.message.startsWith('ERROR:')) {
            term.writeln(`\x1b[1;31m${data.message}\x1b[0m`);
          } else if (data.message.startsWith('SUCCESS:')) {
            term.writeln(`\x1b[1;32m${data.message}\x1b[0m`);
          } else if (data.message.startsWith('MISSING:')) {
            term.writeln(`\x1b[1;33m${data.message}\x1b[0m`);
          } else if (data.message.startsWith('PRESENT:')) {
            term.writeln(`\x1b[1;36m${data.message}\x1b[0m`);
          } else {
            term.writeln(data.message);
          }
        } else if (data.type === 'result') {
          term.writeln(`\x1b[1;34m[RESULT] Results finalized for ${data.strategy}\x1b[0m`);
        }
      } catch (e) {
        // Fallback for raw text
        const text = typeof event.data === 'string' ? event.data : JSON.stringify(event.data);
        term.writeln(text);
      }
    };

    ws.onerror = () => {
      term.writeln(`\x1b[1;31m[SYSTEM] WebSocket error for scan ${scanId}\x1b[0m`);
    };

    ws.onclose = (ev) => {
      isConnectedRef.current = false;
      term.writeln(
        `\x1b[1;33m[SYSTEM] Connection closed (code ${ev.code}) for scan ${scanId}\x1b[0m`
      );
    };

    // 4. Resize handler using the safe fit logic
    const handleResize = () => {
      if (terminalRef.current && terminalRef.current.offsetWidth > 0 && terminalRef.current.offsetHeight > 0) {
        try {
          fitAddonRef.current?.fit();
        } catch (e) {
          // Ignore dimensions errors during resize transitions
        }
      }
    };
    window.addEventListener('resize', handleResize);

    // 5. Cleanup for this effect (new scanId or unmount)
    return () => {
      window.removeEventListener('resize', handleResize);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      // Note: xtermRef.current?.dispose() is handled by the standalone
      // cleanup effect above, which runs only on final unmount.
    };
  }, [scanId]);

  return (
    <div className="bg-card-bg border border-card-border rounded-lg p-2 h-[400px] flex flex-col">
      <div className="flex items-center justify-between mb-2 px-2">
        <h3 className="text-sm font-mono text-gray-400">Terminal Output — Scan: {scanId}</h3>
        <div className="flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neon-green opacity-75 hidden data-[live=true]:inline-flex" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-neon-green" />
          </span>
          <span className="text-xs font-mono text-neon-green">LIVE</span>
        </div>
      </div>
      <div className="flex-1 w-full overflow-hidden" ref={terminalRef} />
    </div>
  );
}
