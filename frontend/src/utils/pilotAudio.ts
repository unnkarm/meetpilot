// PCM conversion runs on the audio thread so UI rendering cannot stall capture.
export async function createPilotCapture(context: AudioContext): Promise<AudioWorkletNode> {
  if (context.sampleRate !== 16000) throw new Error('This browser cannot capture at 16 kHz. Use Chrome or Edge.');
  const script = `class PilotCapture extends AudioWorkletProcessor {
    constructor() { super(); this.samples = new Int16Array(1024); this.offset = 0; }
    process(inputs) {
      const channels = inputs[0];
      if (!channels?.length) return true;
      for (let i = 0; i < channels[0].length; i++) {
        let sample = 0;
        for (const channel of channels) sample += channel[i] / channels.length;
        sample = Math.max(-1, Math.min(1, sample));
        this.samples[this.offset++] = sample < 0 ? sample * 32768 : sample * 32767;
        if (this.offset === this.samples.length) {
          this.port.postMessage(this.samples.buffer, [this.samples.buffer]);
          this.samples = new Int16Array(1024); this.offset = 0;
        }
      }
      return true;
    }
  }; registerProcessor('pilot-capture', PilotCapture);`;
  const url = URL.createObjectURL(new Blob([script], { type: 'text/javascript' }));
  try { await context.audioWorklet.addModule(url); } finally { URL.revokeObjectURL(url); }
  return new AudioWorkletNode(context, 'pilot-capture');
}
