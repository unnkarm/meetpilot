const test = require('node:test');
const assert = require('node:assert/strict');
const { ensureMeetingMicrophone, installMicrophoneControl, setVoiceActivityGuard } = require('./voice_controls.cjs');

test('Google Meet microphone state is idempotent and ignores the settings control', async () => {
  let on = true;
  let clicks = 0;
  const settings = { getAttribute: () => 'Microphone settings', click: () => assert.fail('settings clicked') };
  const microphone = {
    getAttribute: name => name === 'aria-label' ? (on ? 'Turn off microphone' : 'Turn on microphone') : null,
    click: () => { on = !on; clicks++; },
  };
  global.document = { querySelectorAll: () => [settings, microphone] };
  try {
    await ensureMeetingMicrophone({ on: true, platform: 'google_meet' });
    assert.equal(clicks, 0);
    await ensureMeetingMicrophone({ on: false, platform: 'google_meet' });
    assert.equal(on, false);
    await ensureMeetingMicrophone({ on: false, platform: 'google_meet' });
    assert.equal(clicks, 1);
    await ensureMeetingMicrophone({ on: true, platform: 'google_meet' });
    assert.equal(on, true);
    assert.equal(clicks, 2);
  } finally { delete global.document; }
});

test('unavailable microphone reports a failure', async () => {
  global.document = { querySelectorAll: () => [] };
  try {
    await assert.rejects(ensureMeetingMicrophone({ on: true, platform: 'google_meet' }), /unavailable/);
  } finally { delete global.document; }
});

test('adapter replaces only the upstream toggle callback', async () => {
  class Page { async evaluate(fn, arg) { return fn(arg); } }
  installMicrophoneControl(Page);
  const installed = Page.prototype.evaluate;
  installMicrophoneControl(Page);
  assert.equal(Page.prototype.evaluate, installed);
  const page = new Page();
  assert.equal(await page.evaluate(() => 'unrelated', { on: true, platform: 'google_meet' }), 'unrelated');
  let clicked = false;
  global.document = { querySelectorAll: () => [{
    getAttribute: name => name === 'aria-label' ? 'Turn off microphone' : null,
    click: () => { clicked = true; },
  }] };
  try {
    // Match the distinctive callback used by the shipped upstream SpeakController.
    const upstream = ({ on }) => { const selector = 'microphone-button'; void on; return selector; };
    const result = await page.evaluate(upstream, { on: true, platform: 'google_meet' });
    assert.deepEqual(result, { microphone_on: true });
    assert.equal(clicked, false);
  } finally { delete global.document; }
});

test('an older turn cannot mute the microphone while the following turn is active', async () => {
  class Page { async evaluate(fn, arg) { return fn(arg); } }
  installMicrophoneControl(Page);
  const previous = setVoiceActivityGuard(() => true);
  let clicks = 0;
  global.document = { querySelectorAll: () => [{
    getAttribute: name => name === 'aria-label' ? 'Turn off microphone' : null,
    click: () => { clicks++; },
  }] };
  try {
    const upstream = ({ on }) => { const selector = 'microphone-button'; void on; return selector; };
    const result = await new Page().evaluate(upstream, { on: false, platform: 'google_meet' });
    assert.equal(result.preserved_for_playback, true);
    assert.equal(clicks, 0);
  } finally {
    setVoiceActivityGuard(previous);
    delete global.document;
  }
});
