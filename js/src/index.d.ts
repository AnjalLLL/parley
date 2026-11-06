export type EndReason =
  | 'hangup' | 'server_error' | 'ended_by_api' | 'invalid_token' | 'unknown_session'
  | 'max_duration' | 'call_limit' | 'ice_failed' | 'timeout' | 'disconnected' | 'error';

export declare const CLOSE_REASONS: Record<number, EndReason>;

export interface CallEvents {
  connected: void;
  track: MediaStream;
  ended: { reason: EndReason; code?: number };
  error: Error;
}

export declare class Call {
  readonly state: 'connecting' | 'connected' | 'ended';
  readonly localStream: MediaStream;
  readonly remoteStream: MediaStream | null;
  readonly muted: boolean;
  /** Resolves when the call ends. */
  readonly ended: Promise<CallEvents['ended']>;
  /** Returns an unsubscribe function. */
  on<K extends keyof CallEvents>(event: K, fn: (data: CallEvents[K]) => void): () => void;
  /** Mute/unmute the mic; toggles with no argument. Returns the new muted state. */
  mute(muted?: boolean): boolean;
  hangup(): void;
}

export interface ConnectOptions {
  /** session.ice_servers from your backend */
  iceServers?: RTCIceServer[];
  /** Use your own microphone stream instead of requesting one. */
  stream?: MediaStream;
  timeoutMs?: number;
}

/** Start a call; resolves once media is flowing. */
export declare function connect(signalingUrl: string, opts?: ConnectOptions): Promise<Call>;
