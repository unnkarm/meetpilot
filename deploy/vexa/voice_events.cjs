/* Adapter around Vexa's real paplay process; completion means successful exit. */
const { setVoiceActivityGuard } = require('./voice_controls.cjs');
const { AsyncLocalStorage } = require('node:async_hooks');

function installVoiceEvents({ childProcess, http, https, createClient, invocation }) {
  const bus = createClient({ url: invocation.redisUrl });
  bus.on('error', () => {});
  const connected = bus.connect();
  const requests = new Map();
  const processes = new Map();
  const previousGuard = setVoiceActivityGuard(() => requests.size > 0 || processes.size > 0);
  const cancelled = new Set();
  const terminal = new Set();
  const context = new AsyncLocalStorage();
  const remember = (set, id) => {
    set.add(id);
    if (set.size > 256) set.delete(set.values().next().value);
  };
  const emit = (type, id) => {
    if (!id || terminal.has(id)) return;
    if (type !== 'playback_started') remember(terminal, id);
    connected.then(() => bus.publish(
      `meetpilot:voice:${invocation.meeting_id}`,
      JSON.stringify({ type, interaction_id: id })
    )).catch(() => {});
  };
  const ready = connected.then(async () => {
    const controls = bus.duplicate();
    controls.on('error', () => {});
    await controls.connect();
    await controls.subscribe(`bot_commands:meeting:${invocation.meeting_id}`, raw => {
      try {
        const act = JSON.parse(raw);
        if (act.action !== 'speak_stop' && act.action !== 'leave') return;
        const target = act.interaction_id;
        // A stop may arrive before Playwright finishes unmuting the meeting mic
        // and creates the HTTP request. Keep the cancelled interaction ID.
        if (target) remember(cancelled, target);
        for (const [req, record] of requests) {
          if (target && record.id !== target) continue;
          remember(cancelled, record.id);
          requests.delete(req);
          req.destroy();
          if (![...processes.values()].includes(record.id)) emit('playback_interrupted', record.id);
        }
        for (const [child, id] of processes) {
          if (target && id !== target) continue;
          remember(cancelled, id);
          child.stdin?.destroy();
          child.kill('SIGKILL');
        }
      } catch {}
    });
  }).catch(() => {});

  const originals = [];
  for (const transport of new Set([http, https].filter(Boolean))) {
    const request = transport.request;
    originals.push([transport, request]);
    transport.request = function (...args) {
      const options = args[0];
      if (!options || options.path !== '/internal/vexa/v1/audio/speech') {
        return request.apply(this, args);
      }
      const record = { id: null };
      const boundResponses = new WeakSet();
      const bindResponse = res => {
        if (!res || boundResponses.has(res)) return;
        boundResponses.add(res);
        const responseEmit = res.emit;
        // EventEmitter does not bind listeners to their registration context.
        // Restore this request's context when deferred data/end events fire.
        res.emit = function (...events) {
          return context.run(record, () => responseEmit.apply(this, events));
        };
      };
      const callbackIndex = args.findIndex(arg => typeof arg === 'function');
      if (callbackIndex >= 0) {
        const callback = args[callbackIndex];
        // paplay belongs to this response, even if older HTTP callbacks arrive
        // after another voice turn. A global "last voice" mislabels ACKs.
        args[callbackIndex] = res => {
          bindResponse(res);
          return context.run(record, () => callback(res));
        };
      }
      const req = request.apply(this, args);
      const requestEmit = req.emit;
      req.emit = function (type, ...events) {
        if (type === 'response') bindResponse(events[0]);
        return context.run(record, () => requestEmit.call(this, type, ...events));
      };
      const write = req.write;
      req.write = function (data, ...rest) {
        try { record.id = JSON.parse(data.toString()).voice; } catch {}
        if (record.id) requests.set(req, record);
        if (cancelled.has(record.id)) {
          requests.delete(req);
          req.destroy();
          emit('playback_interrupted', record.id);
          return false;
        }
        return write.call(this, data, ...rest);
      };
      req.on('response', res => {
        res.once('close', () => requests.delete(req));
        res.once('error', () => emit(cancelled.has(record.id) ? 'playback_interrupted' : 'playback_failed', record.id));
        if (res.statusCode !== 200) emit('playback_failed', record.id);
      });
      req.on('error', () => {
        requests.delete(req);
        emit(cancelled.has(record.id) ? 'playback_interrupted' : 'playback_failed', record.id);
      });
      return req;
    };
  }
  const spawn = childProcess.spawn;
  childProcess.spawn = function (command, ...args) {
    const child = spawn.call(this, command, ...args);
    const id = context.getStore()?.id;
    if (command === 'paplay' && id) {
      processes.set(child, id);
      child.once('error', () => emit('playback_failed', id));
      child.once('close', code => {
        processes.delete(child);
        emit(cancelled.has(id) ? 'playback_interrupted'
          : code === 0 ? 'playback_complete' : 'playback_failed', id);
      });
      if (cancelled.has(id)) {
        child.stdin?.destroy();
        child.kill('SIGKILL');
      } else {
        emit('playback_started', id);
      }
    }
    return child;
  };
  return { ready, restore() {
    setVoiceActivityGuard(previousGuard);
    childProcess.spawn = spawn;
    for (const [transport, request] of originals) transport.request = request;
  } };
}

module.exports = { installVoiceEvents };

if (process.env.VEXA_BOT_CONFIG) {
  installVoiceEvents({
    childProcess: require('node:child_process'),
    http: require('node:http'),
    https: require('node:https'),
    createClient: require('/app/core/meetings/services/bot/node_modules/redis').createClient,
    invocation: JSON.parse(process.env.VEXA_BOT_CONFIG),
  });
  require('node:module').syncBuiltinESMExports();
}
