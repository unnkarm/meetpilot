import { ApiMeetingDetail, ApiTranscriptSegment } from '../types';

export interface SpeakerColorTheme {
  bg: string;
  border: string;
  text: string;
  avatarBg: string;
  badgeBg: string;
}

const SPEAKER_PALETTES: SpeakerColorTheme[] = [
  {
    bg: 'bg-violet-500/10',
    border: 'border-violet-500/30',
    text: 'text-violet-300',
    avatarBg: 'bg-gradient-to-tr from-violet-600 to-indigo-600',
    badgeBg: 'bg-violet-500/20 text-violet-300 border-violet-500/30',
  },
  {
    bg: 'bg-cyan-500/10',
    border: 'border-cyan-500/30',
    text: 'text-cyan-300',
    avatarBg: 'bg-gradient-to-tr from-cyan-600 to-teal-600',
    badgeBg: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  },
  {
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    text: 'text-amber-300',
    avatarBg: 'bg-gradient-to-tr from-amber-600 to-orange-600',
    badgeBg: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  },
  {
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    text: 'text-emerald-300',
    avatarBg: 'bg-gradient-to-tr from-emerald-600 to-teal-700',
    badgeBg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  },
  {
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/30',
    text: 'text-rose-300',
    avatarBg: 'bg-gradient-to-tr from-rose-600 to-pink-600',
    badgeBg: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
  },
  {
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    text: 'text-blue-300',
    avatarBg: 'bg-gradient-to-tr from-blue-600 to-sky-600',
    badgeBg: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  },
];

/**
 * Deterministically maps a speaker identifier or name to a distinct, consistent color palette.
 */
export function getSpeakerColorTheme(speaker: string): SpeakerColorTheme {
  if (!speaker) return SPEAKER_PALETTES[0];

  // If speaker matches "Speaker N", use N - 1 index directly
  const match = speaker.match(/speaker\s*(\d+)/i);
  if (match) {
    const num = parseInt(match[1], 10);
    return SPEAKER_PALETTES[(num - 1) % SPEAKER_PALETTES.length];
  }

  // Hash the speaker name string to pick consistent index
  let hash = 0;
  for (let i = 0; i < speaker.length; i++) {
    hash = (hash << 5) - hash + speaker.charCodeAt(i);
    hash |= 0;
  }
  const index = Math.abs(hash) % SPEAKER_PALETTES.length;
  return SPEAKER_PALETTES[index];
}

/**
 * Returns clean 2-character initials for a speaker avatar.
 */
export function getSpeakerInitials(speaker: string): string {
  if (!speaker) return 'S1';
  const clean = speaker.trim();

  // If "Speaker 1" -> "S1"
  const match = clean.match(/speaker\s*(\d+)/i);
  if (match) return `S${match[1]}`;

  const parts = clean.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/**
 * Formats duration in seconds to mm:ss (e.g. 9 -> "00:09", 125 -> "02:05").
 */
export function formatTimeSeconds(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '00:00';
  const total = Math.floor(seconds);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

export interface SpeakerAirtime {
  speaker: string;
  durationSeconds: number;
  percentage: number;
  colorTheme: SpeakerColorTheme;
}

export interface MeetingSpeakerStats {
  uniqueSpeakers: string[];
  detectedCount: number;
  participantCount: number;
  displayLabel: string;
  airtime: SpeakerAirtime[];
}

/**
 * Authoritative helper to derive true participant/speaker statistics from meeting detail and transcript.
 */
export function getMeetingSpeakerStats(
  meetingDetail?: ApiMeetingDetail | null,
  transcript?: ApiTranscriptSegment[] | null
): MeetingSpeakerStats {
  const segments = transcript || [];

  // Extract unique, non-empty, trimmed speaker labels
  const uniqueSpeakers = Array.from(
    new Set(
      segments
        .map((s) => s.speaker?.trim())
        .filter((s): s is string => Boolean(s))
    )
  );

  const detectedCount = uniqueSpeakers.length;
  const participantList = meetingDetail?.participants || [];
  const participantCount = participantList.length;

  let displayLabel = '';
  if (detectedCount > 0) {
    if (participantCount > 0 && participantCount !== detectedCount) {
      displayLabel = `${participantCount} participants · ${detectedCount} detected speakers`;
    } else {
      displayLabel = detectedCount === 1 ? '1 speaker detected' : `${detectedCount} speakers detected`;
    }
  } else if (participantCount > 0) {
    displayLabel = participantCount === 1 ? '1 participant' : `${participantCount} participants`;
  } else {
    displayLabel = '1 participant';
  }

  // Calculate participation airtime from transcript timestamps
  const speakerDurations: Record<string, number> = {};
  let totalDiarizedSeconds = 0;

  for (const seg of segments) {
    const dur = Math.max(0, seg.end_time - seg.start_time);
    const spk = seg.speaker?.trim() || 'Speaker 1';
    speakerDurations[spk] = (speakerDurations[spk] || 0) + dur;
    totalDiarizedSeconds += dur;
  }

  const airtime: SpeakerAirtime[] = Object.entries(speakerDurations)
    .map(([spk, dur]) => ({
      speaker: spk,
      durationSeconds: Math.round(dur * 10) / 10,
      percentage: totalDiarizedSeconds > 0 ? Math.round((dur / totalDiarizedSeconds) * 100) : 0,
      colorTheme: getSpeakerColorTheme(spk),
    }))
    .sort((a, b) => b.durationSeconds - a.durationSeconds);

  return {
    uniqueSpeakers,
    detectedCount: detectedCount || participantCount || 1,
    participantCount: participantCount || detectedCount || 1,
    displayLabel,
    airtime,
  };
}
