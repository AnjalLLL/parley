/**
 * Voxwire browser client. No dependencies.
 *
 *   const call = await connect(session.signaling_url, { iceServers: session.ice_servers });
 *   call.on('ended', ({ reason }) => console.log(reason));
 *   call.hangup();
 */

/** Server close codes -> readable reasons. */
export const CLOSE_REASONS = {
  1000: 'hangup',
  1011: 'server_error',
  4000: 'ended_by_api',
  4401: 'invalid_token',
  4404: 'unknown_session',
  4408: 'max_duration',
  4429: 'call_limit',
};

const DEFAULT_ICE = [{ urls: 'stun:stun.l.google.com:19302' }];

export class Call {
  constructor(ws, pc, localStream) {
    this.ws = ws;
    this.pc = pc;
    this.localStream = localStream;
    this.remoteStream = null;
    this.state = 'connecting'; // connecting -> connected -> ended
    this._handlers = {};
    this.ended = new Promise(resolve => this.on('ended', resolve));
  }

  /** Events: connected, track (MediaStream), ended ({reason, code}), error (Error). */
  on(event, fn) {
    (this._handlers[event] ||= []).push(fn);
    return () => { this._handlers[event] = this._handlers[event].filter(f => f !== fn); };
  }

  _emit(event, data) {
    for (const fn of this._handlers[event] || []) {
      try { fn(data); } catch (e) { console.error(e); }
    }
  }

  get muted() {
    return this.localStream.getAudioTracks().every(t => !t.enabled);
  }

  /** Mute or unmute the microphone. With no argument it toggles. Returns the new muted state. */
  mute(muted = !this.muted) {
    this.localStream.getAudioTracks().forEach(t => { t.enabled = !muted; });
    return muted;
  }

  hangup(reason = 'hangup', code) {
    if (this.state === 'ended') return;
    this.state = 'ended';
    try { this.pc.close(); } catch {}
    if (this.ws.readyState <= 1) this.ws.close(1000);
    if (this._ownStream) this.localStream.getTracks().forEach(t => t.stop());
    this._emit('ended', { reason, code });
  }
}

/**
 * Start a call. Resolves once media is flowing; rejects if the server refuses or ICE fails.
 * @param {string} signalingUrl  session.signaling_url from your backend (already carries the token)
 * @param {object} [opts]
 * @param {RTCIceServer[]} [opts.iceServers]  session.ice_servers from your backend
 * @param {MediaStream} [opts.stream]  your own mic stream; otherwise one is requested
 * @param {number} [opts.timeoutMs=15000]
 */
export function connect(signalingUrl, opts = {}) {
  const env = {
    WebSocket: opts.WebSocket || globalThis.WebSocket,
    RTCPeerConnection: opts.RTCPeerConnection || globalThis.RTCPeerConnection,
    getUserMedia: opts.getUserMedia || (c => globalThis.navigator.mediaDevices.getUserMedia(c)),
  };
  return (async () => {
    const ownStream = !opts.stream;
    const localStream = opts.stream || await env.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    const pc = new env.RTCPeerConnection({ iceServers: opts.iceServers?.length ? opts.iceServers : DEFAULT_ICE });
    const ws = new env.WebSocket(signalingUrl);
    const call = new Call(ws, pc, localStream);
    call._ownStream = ownStream;

    const ready = new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error('timed out connecting the call'));
        call.hangup('timeout');
      }, opts.timeoutMs ?? 15000);
      call.on('connected', () => { clearTimeout(timer); resolve(call); });
      call.on('ended', ({ reason }) => { clearTimeout(timer); reject(new Error(`call ended before connecting: ${reason}`)); });
    });
    ready.catch(() => {}); // the caller gets the rejection through the returned promise

    localStream.getTracks().forEach(t => pc.addTrack(t, localStream));
    pc.ontrack = e => { call.remoteStream = e.streams[0]; call._emit('track', e.streams[0]); };
    pc.onicecandidate = e => { if (e.candidate && ws.readyState === 1) ws.send(JSON.stringify({ type: 'ice-candidate', candidate: e.candidate })); };
    pc.oniceconnectionstatechange = () => {
      const s = pc.iceConnectionState;
      if ((s === 'connected' || s === 'completed') && call.state === 'connecting') {
        call.state = 'connected';
        call._emit('connected');
      } else if (s === 'failed') {
        call.hangup('ice_failed');
      }
    };

    ws.onopen = async () => {
      try {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        ws.send(JSON.stringify({ type: 'offer', sdp: offer.sdp }));
      } catch (e) { call._emit('error', e); call.hangup('error'); }
    };
    ws.onmessage = async event => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'answer') await pc.setRemoteDescription({ type: 'answer', sdp: msg.sdp });
        else if (msg.type === 'ice-candidate') await pc.addIceCandidate(msg.candidate);
      } catch (e) { call._emit('error', e); }
    };
    ws.onclose = e => call.hangup(CLOSE_REASONS[e.code] || 'disconnected', e.code);
    ws.onerror = () => call._emit('error', new Error('signaling connection error'));

    return ready;
  })();
}
