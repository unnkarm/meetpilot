/* Correct the upstream speak controller's toggle-only microphone operation. */
const path = require('node:path');
const { createRequire } = require('node:module');
let voiceActivityGuard = () => false;

function setVoiceActivityGuard(guard) {
  const previous = voiceActivityGuard;
  voiceActivityGuard = guard;
  return previous;
}

// This function is serialized by Playwright and runs in the meeting page.
async function ensureMeetingMicrophone({ on, platform }) {
  const labels = platform === 'google_meet'
    ? { muted: /^Turn on microphone\b/i, live: /^Turn off microphone\b/i }
    : platform === 'teams'
      ? { muted: /^(Unmute|Turn on microphone)\b/i, live: /^(Mute|Turn off microphone)\b/i }
      : platform === 'zoom'
        ? { muted: /^Unmute\b/i, live: /^Mute\b/i }
        : platform === 'jitsi'
          ? { muted: /^Unmute microphone\b/i, live: /^Mute microphone\b/i }
          : null;
  if (!labels) throw new Error('Unsupported platform microphone control');
  const find = () => Array.from(document.querySelectorAll('button,[role="button"]')).find(b => {
    const label = b.getAttribute('aria-label') || b.getAttribute('title') || '';
    return labels.muted.test(label) || labels.live.test(label);
  });
  const state = b => labels.live.test(b.getAttribute('aria-label') || b.getAttribute('title') || '');
  let button = find();
  if (!button || button.disabled || button.getAttribute('aria-disabled') === 'true') {
    throw new Error('The meeting microphone control is unavailable');
  }
  if (state(button) !== on) button.click();
  const deadline = Date.now() + 3000;
  while (Date.now() < deadline) {
    button = find();
    if (button && state(button) === on) return { microphone_on: on };
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error('The meeting microphone did not reach the requested state');
}

function installMicrophoneControl(Page) {
  const original = Page.prototype.evaluate;
  if (original.__meetpilotMicControl) return;
  const evaluate = function (fn, arg) {
    // Scope the adapter to the known upstream SpeakController setMic callback.
    if (typeof fn === 'function' && arg && typeof arg.on === 'boolean' && arg.platform
        && fn.toString().includes('void on') && fn.toString().includes('microphone-button')) {
      // A cancelled older SpeakController can finish after the following turn
      // has begun synthesis. Its final mute must not silence that new reply.
      if (!arg.on && voiceActivityGuard()) {
        return Promise.resolve({ microphone_on: true, preserved_for_playback: true });
      }
      return original.call(this, ensureMeetingMicrophone, arg).then(result => {
        console.log(`[meetpilot] microphone ${arg.on ? 'on' : 'off'} confirmed`);
        return result;
      });
    }
    return original.call(this, fn, arg);
  };
  evaluate.__meetpilotMicControl = true;
  Page.prototype.evaluate = evaluate;
}

module.exports = { ensureMeetingMicrophone, installMicrophoneControl, setVoiceActivityGuard };

if (process.env.VEXA_BOT_CONFIG) {
  const browserRequire = createRequire('/app/core/meetings/modules/remote-browser/package.json');
  const playwrightRequire = createRequire(browserRequire.resolve('playwright'));
  const core = path.dirname(playwrightRequire.resolve('playwright-core/package.json'));
  installMicrophoneControl(require(path.join(core, 'lib/client/page.js')).Page);
}
