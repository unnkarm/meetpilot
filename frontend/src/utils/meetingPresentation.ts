import type { ApiMeetingListItem, MeetingStatus } from '../types';

export type MeetingFilter = 'all' | 'live' | 'completed' | 'processing' | 'failed';
export function meetingState(status: MeetingStatus): { label: string; tone: string } {
  if (status === 'in_progress') return { label: 'Live', tone: 'live' };
  if (status === 'completed') return { label: 'Ready', tone: 'success' };
  if (status === 'failed') return { label: 'Needs attention', tone: 'danger' };
  if (status === 'queued') return { label: 'Queued', tone: 'neutral' };
  return { label: status === 'transcribing' ? 'Transcribing' : 'Processing', tone: 'warning' };
}
export function filterMeetings(meetings: ApiMeetingListItem[], query: string, filter: MeetingFilter, sort: 'newest' | 'oldest' = 'newest') {
  const q = query.trim().toLocaleLowerCase();
  return meetings.filter(m => (!q || [m.title, ...m.participants.map(p => p.name)].join(' ').toLocaleLowerCase().includes(q)) && (
    filter === 'all' || (filter === 'live' && m.status === 'in_progress') ||
    (filter === 'completed' && m.status === 'completed') || (filter === 'failed' && m.status === 'failed') ||
    (filter === 'processing' && !['in_progress', 'completed', 'failed'].includes(m.status))
  )).sort((a, b) => (Date.parse(b.created_at) - Date.parse(a.created_at)) * (sort === 'newest' ? 1 : -1));
}
export function canControlMeeting(meeting: ApiMeetingListItem, manager: boolean, actorId?: string) {
  return manager || Boolean(actorId && meeting.created_by === actorId);
}
export function meetingDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}
export function meetingDuration(seconds?: number | null) {
  if (!seconds || seconds <= 0) return '—';
  const minutes = Math.max(1, Math.round(seconds / 60));
  return minutes >= 60 ? `${Math.floor(minutes / 60)}h ${minutes % 60}m` : `${minutes} min`;
}
