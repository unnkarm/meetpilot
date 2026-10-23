import type { ApiTranscriptSegment } from '../types';

export function speechIntervals(segments: ApiTranscriptSegment[], duration: number): [number, number][] {
  const intervals = segments.filter(s => s.text.trim() && Number.isFinite(s.start_time) && Number.isFinite(s.end_time) && s.start_time >= 0 && s.end_time > s.start_time)
    .map(s => [Math.max(0, s.start_time - 0.75), Math.min(duration > 0 ? duration : Infinity, s.end_time + 0.75)] as [number, number])
    .filter(([start, end]) => end > start).sort((a, b) => a[0] - b[0]);
  const merged: [number, number][] = [];
  for (const [start, end] of intervals) {
    const last = merged[merged.length - 1];
    if (last && start <= last[1] + 1.25) last[1] = Math.max(last[1], end);
    else merged.push([start, end]);
  }
  return merged;
}

export function nextSpeechPosition(time: number, intervals: [number, number][]): number | null {
  if (!Number.isFinite(time) || time < 0) return null;
  for (const [start, end] of intervals) {
    if (time >= start && time <= end) return null;
    if (time < start) return start - time > 2 ? start : null;
  }
  // Do not skip untranscribed audio after the last turn.
  return null;
}

export function pacingRate(time: number, segments: ApiTranscriptSegment[], baseRate: number): number {
  const segment = segments.find(s => s.start_time <= time && s.end_time >= time);
  if (!segment || segment.end_time - segment.start_time < 3) return baseRate;
  const words = segment.text.trim().split(/\s+/u).filter(Boolean).length;
  if (words < 3) return baseRate;
  const wpm = words * 60 / (segment.end_time - segment.start_time);
  const factor = wpm < 105 ? 1.25 : wpm > 190 ? 0.85 : 1;
  return Math.max(0.75, Math.min(2, Math.round(baseRate * factor * 100) / 100));
}
