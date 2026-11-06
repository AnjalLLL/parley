import { test } from 'node:test';
import assert from 'node:assert/strict';
import { connect } from '../src/index.js';

class FakeTrack { enabled = true; stopped = false; stop() { this.stopped = true; } }
class FakeStream {
  tracks = [new FakeTrack()];
  getTracks() { return this.tracks; }
  getAudioTracks() { return this.tracks; }
}

class FakeWS {
  static last;
  readyState = 0; sent = [];
  constructor(url) { this.url = url; FakeWS.last = this; queueMicrotask(() => { this.readyState = 1; this.onopen?.(); }); }
  send(m) { this.sent.push(JSON.parse(m)); }
  close(code = 1000) { if (this.readyState > 1) return; this.readyState = 3; this.onclose?.({ code }); }
  serverClose(code) { this.readyState = 3; this.onclose?.({ code }); }
  serverSend(obj) { this.onmessage?.({ data: JSON.stringify(obj) }); }
}

class FakePC {
  static last;
  iceConnectionState = 'new'; added = []; remote = null; candidates = []; closed = false;
  constructor(cfg) { this.cfg = cfg; FakePC.last = this; }
  addTrack(t) { this.added.push(t); }
  async createOffer() { return { type: 'offer', sdp: 'v=0 offer' }; }
  async setLocalDescription() {}
  async setRemoteDescription(d) { this.remote = d; }
  async addIceCandidate(c) { this.candidates.push(c); }
  close() { this.closed = true; }
  setIce(s) { this.iceConnectionState = s; this.oniceconnectionstatechange?.(); }
}

const env = (extra = {}) => ({ WebSocket: FakeWS, RTCPeerConnection: FakePC, getUserMedia: async () => new FakeStream(), ...extra });
const tick = () => new Promise(r => setTimeout(r, 0));

test('full call: offer, answer, ice, connected, mute, hangup', async () => {
  const p = connect('ws://x/ws/signaling/s1?token=t', { ...env(), iceServers: [{ urls: 'turn:t' }] });
  await tick();
  const ws = FakeWS.last, pc = FakePC.last;
  assert.equal(ws.url, 'ws://x/ws/signaling/s1?token=t');
  assert.deepEqual(pc.cfg.iceServers, [{ urls: 'turn:t' }]);
  assert.deepEqual(ws.sent[0], { type: 'offer', sdp: 'v=0 offer' });

  ws.serverSend({ type: 'answer', sdp: 'v=0 answer' });
  ws.serverSend({ type: 'ice-candidate', candidate: { candidate: 'c1' } });
  pc.onicecandidate({ candidate: { candidate: 'local' } });
  await tick();
  assert.equal(pc.remote.sdp, 'v=0 answer');
  assert.equal(pc.candidates[0].candidate, 'c1');
  assert.equal(ws.sent[1].type, 'ice-candidate');

  pc.setIce('connected');
  const call = await p;
  assert.equal(call.state, 'connected');
  assert.equal(call.mute(), true);
  assert.equal(call.muted, true);
  assert.equal(call.mute(false), false);

  call.hangup();
  const end = await call.ended;
  assert.equal(end.reason, 'hangup');
  assert.ok(pc.closed);
  assert.ok(call.localStream.getTracks()[0].stopped, 'own mic stream is stopped');
});

test('server rejection rejects connect with a readable reason', async () => {
  const p = connect('ws://x/ws/signaling/bad', env());
  await tick();
  FakeWS.last.serverClose(4401);
  await assert.rejects(p, /invalid_token/);
});

test('server ending a live call reports the reason', async () => {
  const p = connect('ws://x/ws/signaling/s', env());
  await tick();
  FakePC.last.setIce('connected');
  const call = await p;
  FakeWS.last.serverClose(4408);
  assert.deepEqual(await call.ended, { reason: 'max_duration', code: 4408 });
});

test('times out when ICE never connects', async () => {
  await assert.rejects(connect('ws://x/s', { ...env(), timeoutMs: 20 }), /timed out/);
});

test('a caller-provided stream is not stopped on hangup', async () => {
  const stream = new FakeStream();
  const p = connect('ws://x/s', { ...env(), stream });
  await tick();
  FakePC.last.setIce('completed');
  (await p).hangup();
  assert.equal(stream.tracks[0].stopped, false);
});
