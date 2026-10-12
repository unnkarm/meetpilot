const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { installVoiceEvents } = require('./voice_events.cjs');

async function harness() {
  const events = [];
  const controls = new EventEmitter();
  controls.connect = async () => {};
  controls.subscribe = async (channel, callback) => { controls.command = callback; };
  const bus = new EventEmitter();
  bus.connect = async () => {};
  bus.duplicate = () => controls;
  bus.publish = async (channel, raw) => events.push(JSON.parse(raw));
  const children = [];
  const childProcess = { spawn() {
    const child = new EventEmitter();
    child.stdin = { destroy() { child.stdinDestroyed = true; } };
    child.kill = () => { child.killed = true; child.emit('close', null); };
    children.push(child);
    return child;
  } };
  const http = { request(...args) {
    const req = new EventEmitter();
    const callback = args.find(arg => typeof arg === 'function');
    if (callback) req.on('response', callback);
    req.write = data => { req.written = data; return true; };
    req.destroy = () => { req.destroyed = true; req.emit('error', new Error('aborted')); };
    return req;
  } };
  const adapter = installVoiceEvents({ childProcess, http, createClient: () => bus,
    invocation: { meeting_id: 71, redisUrl: 'redis://fake' } });
  await adapter.ready;
  const request = (id, deferredEvent) => {
    const req = http.request({ path: '/internal/vexa/v1/audio/speech' }, res => {
      if (res.statusCode === 200) {
        const play = () => { req.player = childProcess.spawn('paplay', []); };
        if (deferredEvent) res.once(deferredEvent, play);
        else play();
      }
    });
    req.write(JSON.stringify({ input: 'Answer.', voice: id }));
    return req;
  };
  const respond = (req, statusCode = 200) => {
    const res = new EventEmitter();
    res.statusCode = statusCode;
    req.emit('response', res);
    return res;
  };
  const stop = id => controls.command(JSON.stringify({ action: 'speak_stop', ...(id ? { interaction_id: id } : {}) }));
  const settle = () => new Promise(resolve => setImmediate(resolve));
  return { events, children, request, respond, stop, settle, restore: adapter.restore };
}

test('successful paplay exit acknowledges its own request', async () => {
  const h = await harness();
  try {
    const req = h.request('turn-1');
    h.respond(req);
    req.player.emit('close', 0);
    await h.settle();
    assert.deepEqual(h.events, [
      { type: 'playback_started', interaction_id: 'turn-1' },
      { type: 'playback_complete', interaction_id: 'turn-1' },
    ]);
  } finally { h.restore(); }
});

test('late HTTP responses retain request IDs after a following turn begins', async () => {
  const h = await harness();
  try {
    const earlier = h.request('earlier');
    const following = h.request('following');
    h.respond(earlier);
    h.respond(following, 500);
    earlier.player.emit('close', 0);
    await h.settle();
    assert.deepEqual(h.events, [
      { type: 'playback_started', interaction_id: 'earlier' },
      { type: 'playback_failed', interaction_id: 'following' },
      { type: 'playback_complete', interaction_id: 'earlier' },
    ]);
  } finally { h.restore(); }
});

test('deferred data/end callbacks retain IDs across overlapping response streams', async () => {
  const h = await harness();
  try {
    const earlier = h.request('deferred-data', 'data');
    const following = h.request('deferred-end', 'end');
    const firstResponse = h.respond(earlier);
    const nextResponse = h.respond(following);
    // These emits run after both response callbacks returned, with no ALS
    // context inherited by this caller. Listener registration alone cannot help.
    nextResponse.emit('end');
    firstResponse.emit('data', Buffer.from('pcm'));
    earlier.player.emit('close', 0);
    following.player.emit('close', 0);
    await h.settle();
    assert.deepEqual(h.events, [
      { type: 'playback_started', interaction_id: 'deferred-end' },
      { type: 'playback_started', interaction_id: 'deferred-data' },
      { type: 'playback_complete', interaction_id: 'deferred-data' },
      { type: 'playback_complete', interaction_id: 'deferred-end' },
    ]);
    assert.ok(h.events.every(event => typeof event.interaction_id === 'string'));
  } finally { h.restore(); }
});

test('cancelled deferred playback cannot resurrect after another response starts', async () => {
  const h = await harness();
  try {
    const earlier = h.request('deferred-cancelled', 'data');
    const firstResponse = h.respond(earlier);
    h.stop('deferred-cancelled');
    const following = h.request('next-answer');
    h.respond(following);
    firstResponse.emit('data', Buffer.from('late-pcm'));
    assert.equal(earlier.player.killed, true);
    assert.equal(following.player.killed, undefined);
    following.player.emit('close', 0);
    await h.settle();
    assert.deepEqual(h.events, [
      { type: 'playback_interrupted', interaction_id: 'deferred-cancelled' },
      { type: 'playback_started', interaction_id: 'next-answer' },
      { type: 'playback_complete', interaction_id: 'next-answer' },
    ]);
  } finally { h.restore(); }
});

test('paplay errors and nonzero exits are failures, not human interruptions', async () => {
  const h = await harness();
  try {
    const failedExit = h.request('nonzero');
    h.respond(failedExit);
    failedExit.player.emit('close', 1);
    const spawnError = h.request('spawn-error');
    h.respond(spawnError);
    spawnError.player.emit('error', new Error('paplay missing'));
    spawnError.player.emit('close', -1);
    await h.settle();
    assert.deepEqual(h.events.filter(event => event.type !== 'playback_started'), [
      { type: 'playback_failed', interaction_id: 'nonzero' },
      { type: 'playback_failed', interaction_id: 'spawn-error' },
    ]);
  } finally { h.restore(); }
});

test('an interruption before synthesis begins cancels the late HTTP request', async () => {
  const h = await harness();
  try {
    h.stop('cancelled-before-http');
    const req = h.request('cancelled-before-http');
    assert.equal(req.destroyed, true);
    assert.equal(req.written, undefined);
    await h.settle();
    assert.deepEqual(h.events, [{ type: 'playback_interrupted', interaction_id: 'cancelled-before-http' }]);
  } finally { h.restore(); }
});

test('pending request interruption is correlated and never reported as synthesis failure', async () => {
  const h = await harness();
  try {
    const earlier = h.request('cancelled');
    const following = h.request('next');
    h.stop('cancelled');
    assert.equal(earlier.destroyed, true);
    assert.equal(following.destroyed, undefined);
    h.respond(following);
    following.player.emit('close', 0);
    await h.settle();
    assert.deepEqual(h.events, [
      { type: 'playback_interrupted', interaction_id: 'cancelled' },
      { type: 'playback_started', interaction_id: 'next' },
      { type: 'playback_complete', interaction_id: 'next' },
    ]);
  } finally { h.restore(); }
});

test('active playback interruption kills the buffer and emits one terminal ACK', async () => {
  const h = await harness();
  try {
    const req = h.request('active');
    h.respond(req).emit('close');
    h.stop();
    assert.equal(req.player.stdinDestroyed, true);
    assert.equal(req.player.killed, true);
    req.player.emit('close', 0);
    await h.settle();
    assert.deepEqual(h.events, [
      { type: 'playback_started', interaction_id: 'active' },
      { type: 'playback_interrupted', interaction_id: 'active' },
    ]);
  } finally { h.restore(); }
});

test('a request transport error retains its own interaction ID', async () => {
  const h = await harness();
  try {
    const earlier = h.request('earlier-error');
    h.request('following');
    earlier.emit('error', new Error('connection closed'));
    await h.settle();
    assert.deepEqual(h.events, [{ type: 'playback_failed', interaction_id: 'earlier-error' }]);
  } finally { h.restore(); }
});
