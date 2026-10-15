import type { WsEventEnvelope } from '../types';
import { getApiBaseUrl, getBackendBaseUrl, getAuthHeaders, isApprovedBackendOrigin } from '../api';

type EventHandler<T = any> = (payload: T, envelope: WsEventEnvelope<T>) => void;
type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export class RealtimeClient {
  private ws: WebSocket | null = null;
  private token: string | null = null;
  private status: ConnectionStatus = 'disconnected';
  private listeners: Map<string, Set<EventHandler>> = new Map();
  private statusListeners: Set<(status: ConnectionStatus) => void> = new Set();
  private activeScopes: Set<string> = new Set();
  private reconnectAttempts = 0;
  private reconnectTimer: number | null = null;
  private pingTimer: number | null = null;
  private isManuallyClosed = false;
  private connectionEpoch = 0;

  constructor() {
    this.handleVisibilityChange = this.handleVisibilityChange.bind(this);
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', this.handleVisibilityChange);
    }
  }

  private handleVisibilityChange() {
    if (document.visibilityState === 'visible' && this.token && this.status === 'disconnected' && !this.isManuallyClosed) {
      this.reconnectAttempts = 0;
      this.connect(this.token);
    }
  }

  private async resolveUrl(_token?: string): Promise<string> {
    const apiBase = getApiBaseUrl();
    const backendBase = getBackendBaseUrl();

    // 1. Enforce destination trust boundary before acquiring ticket
    if (backendBase) {
      if (!isApprovedBackendOrigin(backendBase)) {
        throw new Error('Native backend origin is unconfigured or unapproved');
      }
    } else {
      // For web browsers, enforce current website origin and reject conflicting WS overrides
      const configuredWs = (import.meta as any).env?.VITE_WS_URL;
      if (configuredWs) {
        try {
          const wsParsed = new URL(configuredWs, typeof window !== 'undefined' ? window.location.href : 'http://localhost');
          const webHost = typeof window !== 'undefined' ? window.location.host : 'localhost';
          if (wsParsed.host !== webHost) {
            throw new Error(`Conflicting VITE_WS_URL (${wsParsed.host}) does not match website origin (${webHost})`);
          }
        } catch (e: any) {
          throw new Error(`Invalid or conflicting VITE_WS_URL: ${e.message || e}`);
        }
      }
    }

    const ticketUrl = `${apiBase}/auth/ws-ticket`;
    const authHeaders = getAuthHeaders(ticketUrl);
    if (!authHeaders['Authorization']) {
      throw new Error('Cannot acquire WebSocket ticket: credentials rejected for unapproved destination');
    }

    const response = await fetch(ticketUrl, {
      method: 'POST',
      headers: authHeaders,
      cache: 'no-store',
    });
    if (!response.ok) throw new Error(`WebSocket ticket request failed (${response.status})`);
    const data: { ticket?: string } = await response.json();
    if (!data.ticket) throw new Error('WebSocket ticket missing from server response');

    let base: string;
    if (backendBase) {
      const parsed = new URL(backendBase);
      const wsProto = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
      base = `${wsProto}//${parsed.host}/ws`;
    } else {
      const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';
      const proto = isHttps ? 'wss:' : 'ws:';
      const host = typeof window !== 'undefined' ? window.location.host : 'localhost:8000';
      base = `${proto}//${host}/ws`;
    }
    const url = new URL(base, typeof window !== 'undefined' ? window.location.href : 'http://localhost');
    url.searchParams.set('ticket', data.ticket);
    return url.toString();
  }

  public connect(token: string) {
    if (this.token === token && (this.status === 'connected' || this.status === 'connecting')) return;
    if (this.ws && (this.status === 'connected' || this.status === 'connecting')) {
      this.disconnect();
    }

    this.token = token;
    this.isManuallyClosed = false;
    this.setStatus(this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting');
    const epoch = ++this.connectionEpoch;

    this.resolveUrl(token).then((url) => {
      if (epoch !== this.connectionEpoch || this.isManuallyClosed || this.token !== token) return;
      const socket = new WebSocket(url);
      this.ws = socket;

      socket.onopen = () => {
        if (this.ws !== socket) return;
        this.reconnectAttempts = 0;
        this.setStatus('connected');
        this.startHeartbeat();

        // Re-subscribe to remembered scopes
        for (const scope of this.activeScopes) {
          this.send({ action: 'subscribe', scope });
        }
      };

      socket.onmessage = (event) => {
        try {
          const envelope = JSON.parse(event.data);
          if (envelope.type === 'pong') return;

          // Dispatch by event type
          if (envelope.type) {
            const handlers = this.listeners.get(envelope.type);
            if (handlers) {
              for (const handler of handlers) {
                try {
                  handler(envelope.payload, envelope);
                } catch (err) {
                  console.error(`Error in event listener for ${envelope.type}:`, err);
                }
              }
            }
          }

          // Wildcard listeners ('*')
          const wildcards = this.listeners.get('*');
          if (wildcards) {
            for (const handler of wildcards) {
              try {
                handler(envelope.payload, envelope);
              } catch (err) {
                console.error('Error in wildcard event listener:', err);
              }
            }
          }
        } catch (e) {
          console.warn('Failed to parse WebSocket message:', e);
        }
      };

      socket.onclose = () => {
        if (this.ws !== socket) return;
        this.stopHeartbeat();
        this.ws = null;
        if (!this.isManuallyClosed) {
          this.setStatus('disconnected');
          this.scheduleReconnect();
        } else {
          this.setStatus('disconnected');
        }
      };

      socket.onerror = () => {
        // onclose will trigger next
      };
    }).catch((e) => {
      if (epoch !== this.connectionEpoch || this.isManuallyClosed) return;
      console.error('Failed to establish WebSocket:', e);
      this.scheduleReconnect();
    });
  }

  public disconnect() {
    this.connectionEpoch++;
    this.isManuallyClosed = true;
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus('disconnected');
  }

  private scheduleReconnect() {
    if (this.isManuallyClosed || !this.token) return;
    this.reconnectAttempts++;
    this.setStatus('reconnecting');

    // Exponential backoff with jitter (max 12s)
    const baseDelay = Math.min(12000, 1000 * Math.pow(1.5, Math.min(this.reconnectAttempts, 6)));
    const jitter = Math.random() * 500;
    const delay = Math.round(baseDelay + jitter);

    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = window.setTimeout(() => {
      if (this.token && !this.isManuallyClosed) {
        this.connect(this.token);
      }
    }, delay);
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.pingTimer = window.setInterval(() => {
      this.send({ action: 'ping' });
    }, 20000);
  }

  private stopHeartbeat() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  public send(payload: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  public subscribe(scope: string) {
    this.activeScopes.add(scope);
    this.send({ action: 'subscribe', scope });
  }

  public unsubscribe(scope: string) {
    this.activeScopes.delete(scope);
    this.send({ action: 'unsubscribe', scope });
  }

  public on<T = any>(eventType: string, handler: EventHandler<T>): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(handler);
    return () => {
      this.listeners.get(eventType)?.delete(handler);
    };
  }

  public onStatusChange(callback: (status: ConnectionStatus) => void): () => void {
    this.statusListeners.add(callback);
    callback(this.status);
    return () => {
      this.statusListeners.delete(callback);
    };
  }

  private setStatus(status: ConnectionStatus) {
    this.status = status;
    for (const listener of this.statusListeners) {
      try {
        listener(status);
      } catch (err) {
        console.error('Error in status listener:', err);
      }
    }
  }

  public getStatus(): ConnectionStatus {
    return this.status;
  }

  public isConnected(): boolean {
    return this.status === 'connected';
  }
}

// Global realtime singleton
export const realtime = new RealtimeClient();
