import { useEffect, useState } from 'react';
import { ArrowRight, Video, CheckSquare2, Clock3, CircleCheck, BookOpen, Users, Upload, Radio, ArrowUpRight } from 'lucide-react';
import type { ApiMeetingListItem, ApiTask } from '../../types';
import { MeetingRows } from './MeetingLibrary';
import { filterMeetings } from '../../utils/meetingPresentation';
interface Props { name: string; meetings: ApiMeetingListItem[]; tasks: ApiTask[]; loading?: boolean; error?: string; onRetry: () => void; onOpen: (id: string) => void; onNavigate: (tab: 'meetings' | 'kanban' | 'knowledge' | 'team') => void; onJoin: () => void; onUpload: () => void; onDemo: () => void; exploringDemo: boolean; manager: boolean; isDemo?: boolean; documentCount: number; memberCount: number }
export function WorkspaceOverview(p: Props) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const updateClock = () => {
      if (document.visibilityState === 'visible') setNow(new Date());
    };
    const timer = window.setInterval(updateClock, 60_000);
    window.addEventListener('focus', updateClock);
    document.addEventListener('visibilitychange', updateClock);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('focus', updateClock);
      document.removeEventListener('visibilitychange', updateClock);
    };
  }, []);
  // Date uses the browser's local timezone, including daylight saving changes.
  const hour = now.getHours();
  const greeting = hour >= 5 && hour < 12 ? 'Good morning' : hour >= 12 && hour < 18 ? 'Good afternoon' : 'Good evening';
  const pending = p.tasks.filter(t => t.status !== 'done');
  const live = p.meetings.filter(m => m.status === 'in_progress');
  const ready = p.meetings.filter(m => m.status === 'completed');
  const hours = (p.meetings.reduce((sum, m) => sum + (m.duration_seconds || 0), 0) / 3600).toFixed(1);
  const metrics = [{ label: 'Meetings captured', value: p.meetings.length, detail: `${ready.length} ready to review`, icon: Video }, { label: p.manager ? 'Open action items' : 'My open action items', value: pending.length, detail: `${p.tasks.filter(t => t.status === 'doing').length} in progress`, icon: CheckSquare2 }, { label: 'Meeting hours', value: hours, detail: 'Total recorded duration', icon: Clock3 }, { label: 'Completed actions', value: p.tasks.filter(t => t.status === 'done').length, detail: p.manager ? 'Across the workspace' : 'Assigned to you', icon: CircleCheck }];
  return <div className="space-y-7"><div className="mp-page-heading"><div><p className="mp-eyebrow">Workspace overview</p><h1>{greeting}, {p.name}.</h1><p>A clear view of your conversations, decisions and next steps.</p></div><span className="mp-today">{now.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</span></div>
    {p.error && <div className="mp-error-state" role="alert"><p>Could not load meetings. {p.error}</p><button className="mp-button mp-button-secondary" onClick={p.onRetry}>Try again</button></div>}
    {!!live.length && <div className="mp-live-notice"><Radio size={18} /><div><strong>{live.length === 1 ? live[0].title : `${live.length} live meetings`}</strong><span>Follow the transcript and open your voice co-pilot.</span></div><button onClick={() => p.onOpen(live[0].id)}>Open live meeting <ArrowRight size={15} /></button></div>}
    {!p.loading && !p.error && !p.meetings.length && <section className="mp-getting-started"><div><span className="mp-eyebrow">Get started</span><h2>Turn your next meeting into clear next steps.</h2><p>Start with a live call or a recording. Your transcript, decisions and follow-ups will stay together.</p><div className="flex gap-2 flex-wrap"><button className="mp-button mp-button-primary" onClick={p.onJoin}><Video size={16} />Join a meeting</button><button className="mp-button mp-button-secondary" onClick={p.onUpload}><Upload size={15} />Upload a recording</button><button className="mp-button mp-button-quiet" disabled={p.exploringDemo} onClick={p.onDemo}>{p.exploringDemo ? 'Opening…' : 'Explore sample workspace'}<ArrowUpRight size={14} /></button></div></div><div className="mp-getting-started-art" aria-hidden="true"><span>01 <strong>Capture the conversation</strong></span><span>02 <strong>Review the evidence</strong></span><span>03 <strong>Move work forward</strong></span></div></section>}
    <div className="mp-metric-grid">{metrics.map(m => <section className="mp-metric" key={m.label}><div><span>{m.label}</span><m.icon size={17} /></div><strong>{p.loading ? '—' : m.value}</strong><small>{m.detail}</small></section>)}</div>
    <div className="mp-overview-grid"><section className="mp-panel"><div className="mp-panel-heading"><div><h2>Recent meetings</h2><p>Your latest conversations and their outcomes.</p></div><button className="mp-text-button" onClick={() => p.onNavigate('meetings')}>View all <ArrowRight size={14} /></button></div>{p.loading ? <div className="mp-empty" role="status">Loading meetings…</div> : p.meetings.length ? <MeetingRows meetings={filterMeetings(p.meetings, '', 'all').slice(0, 5)} onOpen={p.onOpen} /> : <div className="mp-empty"><Video size={26} /><h3>No meetings yet</h3><p>Your recordings and live calls will appear here.</p></div>}<div className="mp-panel-footer"><BookOpen size={14} />Summaries and decisions link back to the conversation.</div></section>
    <section className="mp-panel"><div className="mp-panel-heading"><div><h2>{p.manager ? 'Next actions' : 'My next actions'}</h2><p>Follow through on what was agreed.</p></div><button className="mp-icon-button" onClick={() => p.onNavigate('kanban')} aria-label="View action items"><ArrowUpRight size={17} /></button></div>{pending.length ? <div className="mp-task-list">{pending.slice(0, 5).map(t => <button key={t.id} onClick={() => p.onNavigate('kanban')} className="mp-task-row"><span className="mp-task-checkbox" /><div className="min-w-0 flex-1"><strong>{t.title}</strong><small>{t.assignee_name || 'Unassigned'}<span>·</span>{t.due_date || 'No deadline'}</small></div><span className={`mp-priority mp-priority-${t.priority}`} title={`${t.priority} priority`} /></button>)}</div> : <div className="mp-empty"><CheckSquare2 size={26} /><h3>No open actions</h3><p>Action items from your meetings will appear here.</p></div>}<button className="mp-panel-footer mp-footer-link" onClick={() => p.onNavigate('kanban')}>Open action board <ArrowRight size={14} /></button></section></div>
    <div className="mp-quick-links"><button onClick={() => p.onNavigate('knowledge')}><span className="mp-quick-icon"><BookOpen size={19} /></span><span><strong>Workspace knowledge</strong><small>{p.documentCount} documents · Ask questions with sources</small></span><ArrowUpRight size={17} /></button><button onClick={() => p.onNavigate('team')}><span className="mp-quick-icon"><Users size={19} /></span><span><strong>People & access</strong><small>{p.memberCount} members · {p.manager ? 'Manage your team and join requests' : 'See your workspace team'}</small></span><ArrowUpRight size={17} /></button></div>
  </div>;
}
