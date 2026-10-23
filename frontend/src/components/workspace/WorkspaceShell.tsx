import { ThemeToggle } from '../ThemeToggle';
import React, { useEffect, useRef, useState } from 'react';
import { LayoutDashboard, Video, CheckSquare2, BookOpen, Search, BarChart3, Users, Plug, Bell, Settings, ChevronDown, Plus, Upload, Mic, Menu, X, LogOut, ArrowUpRight, Radio, Building2, Check } from 'lucide-react';
import { MeetPilotLogo } from '../Logo';
import type { ApiWorkspace } from '../../types';

export type WorkspaceTab = 'dashboard' | 'meetings' | 'meeting' | 'kanban' | 'knowledge' | 'search' | 'analytics' | 'team' | 'integrations' | 'notifications' | 'settings';
export const workspaceNavigation = [
  { id: 'dashboard', label: 'Overview', icon: LayoutDashboard, group: 'Workspace' },
  { id: 'meetings', label: 'Meetings', icon: Video, group: 'Workspace' },
  { id: 'kanban', label: 'Action items', icon: CheckSquare2, group: 'Workspace' },
  { id: 'knowledge', label: 'Knowledge', icon: BookOpen, group: 'Workspace' },
  { id: 'search', label: 'Search', icon: Search, group: 'Workspace' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, group: 'Manage' },
  { id: 'team', label: 'People & access', icon: Users, group: 'Manage' },
  { id: 'integrations', label: 'Integrations', icon: Plug, group: 'Manage' },
] as const;
interface Props {
  children: React.ReactNode; activeTab: WorkspaceTab; onNavigate: (tab: WorkspaceTab) => void;
  workspace: ApiWorkspace; workspaces: ApiWorkspace[]; onSwitchWorkspace: (id: string) => void;
  onCreateWorkspace: () => void; onJoinWorkspace: () => void; onHome: () => void;
  onUpload: () => void; onRecord: () => void; onJoinMeeting: () => void; onSignOut: () => void;
  userName: string; userEmail?: string; avatarUrl?: string; manager: boolean; pendingRequests: number; notificationCount: number;
}
export function WorkspaceShell(p: Props) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const switcher = useRef<HTMLDivElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const mobileNav = useRef<HTMLElement>(null);
  useEffect(() => {
    function dismiss(e: PointerEvent) { if (!switcher.current?.contains(e.target as Node)) setSwitcherOpen(false); }
    document.addEventListener('pointerdown', dismiss);
    return () => document.removeEventListener('pointerdown', dismiss);
  }, []);
  useEffect(() => {
    if (!mobileOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    mobileNav.current?.querySelector<HTMLButtonElement>('button')?.focus();
    function key(e: KeyboardEvent) {
      if (e.key === 'Escape') { setMobileOpen(false); menuButton.current?.focus(); }
      if (e.key === 'Tab') {
        const items = mobileNav.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)');
        if (!items?.length) return;
        const first = items[0], last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    }
    document.addEventListener('keydown', key);
    return () => { document.body.style.overflow = previous; document.removeEventListener('keydown', key); };
  }, [mobileOpen]);
  const navigate = (tab: WorkspaceTab) => { p.onNavigate(tab); setMobileOpen(false); };
  const title = p.activeTab === 'meeting' ? 'Meeting workspace' : p.activeTab === 'settings' ? 'Settings' : p.activeTab === 'notifications' ? 'Activity' : workspaceNavigation.find(n => n.id === p.activeTab)?.label;
  return <div className="mp-app">
    <a className="mp-skip" href="#workspace-content">Skip to content</a>
    {mobileOpen && <button className="mp-nav-backdrop" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <aside ref={mobileNav} className={`mp-sidebar ${mobileOpen ? 'is-open' : ''}`} aria-label="Workspace navigation" role={mobileOpen ? 'dialog' : undefined} aria-modal={mobileOpen || undefined}>
      <div className="mp-sidebar-brand"><button onClick={p.onHome} aria-label="MeetPilot home"><MeetPilotLogo className="h-8" /></button><button className="mp-mobile-close mp-icon-button" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={18} /></button></div>
      <div className="mp-workspace-switch" ref={switcher}>
        <button className="mp-workspace-trigger" onClick={() => setSwitcherOpen(!switcherOpen)} aria-expanded={switcherOpen} aria-controls="workspace-switcher">
          <span className="mp-workspace-avatar">{p.workspace.name.slice(0, 1).toUpperCase()}</span><span className="min-w-0 flex-1 text-left"><strong className="block truncate">{p.workspace.name}</strong><small>{p.workspace.is_demo ? 'Sample workspace' : p.workspace.current_role === 'owner' ? 'Owner' : p.manager ? 'Manager' : 'Member'}</small></span><ChevronDown size={14} />
        </button>
        {switcherOpen && <div className="mp-dropdown" id="workspace-switcher"><p className="mp-menu-caption">Your workspaces</p>{p.workspaces.map(w => <button key={w.id} onClick={() => { p.onSwitchWorkspace(w.id); setSwitcherOpen(false); setMobileOpen(false); }}><Building2 size={15} /><span className="truncate flex-1 text-left">{w.name}</span>{w.id === p.workspace.id && <Check size={14} />}</button>)}<div className="mp-menu-divider" /><button onClick={() => { p.onCreateWorkspace(); setSwitcherOpen(false); }}><Plus size={15} />Create workspace</button><button onClick={() => { p.onJoinWorkspace(); setSwitcherOpen(false); }}> <Users size={15} />Join with a code</button></div>}
      </div>
      <nav className="mp-nav">{['Workspace', 'Manage'].map(group => <div key={group}><p className="mp-nav-label">{group}</p>{workspaceNavigation.filter(n => n.group === group && (n.id !== 'integrations' || p.manager)).map(n => {
        const active = p.activeTab === n.id || (n.id === 'meetings' && p.activeTab === 'meeting');
        return <button key={n.id} onClick={() => navigate(n.id)} aria-current={active ? 'page' : undefined} className={`mp-nav-item ${active ? 'is-active' : ''}`}><n.icon size={18} /><span>{n.label}</span>{n.id === 'team' && p.pendingRequests > 0 && <span className="mp-nav-count">{p.pendingRequests}</span>}</button>;
      })}</div>)}</nav>
      <div className="mp-sidebar-bottom"><button className={`mp-nav-item ${p.activeTab === 'notifications' ? 'is-active' : ''}`} onClick={() => navigate('notifications')}><Bell size={18} /><span>Activity</span>{p.notificationCount > 0 && <span className="mp-nav-count">{p.notificationCount}</span>}</button><button className={`mp-nav-item ${p.activeTab === 'settings' ? 'is-active' : ''}`} onClick={() => navigate('settings')}><Settings size={18} /><span>Settings</span></button>
        <div className="mp-user"><span className="mp-user-avatar">{p.avatarUrl ? <img src={p.avatarUrl} alt="" /> : p.userName.slice(0, 1)}</span><div className="min-w-0 flex-1"><strong className="block truncate">{p.userName}</strong><small className="block truncate">{p.userEmail}</small></div><button onClick={p.onSignOut} className="mp-icon-button" title="Sign out" aria-label="Sign out"><LogOut size={16} /></button></div>
      </div>
    </aside>
    <div className="mp-main-frame"><header className="mp-toolbar"><div className="flex items-center gap-3 min-w-0"><button ref={menuButton} className="mp-mobile-menu mp-icon-button" onClick={() => setMobileOpen(true)} aria-label="Open navigation" aria-expanded={mobileOpen}><Menu size={20} /></button><span className="mp-breadcrumb">Workspace <span>/</span> <strong>{title}</strong></span></div><div className="mp-toolbar-actions"><ThemeToggle /><button className="mp-icon-button mp-search-shortcut" onClick={() => navigate('search')} aria-label="Search workspace"><Search size={18} /></button><button className="mp-button mp-button-quiet mp-record-button" aria-label="Record" onClick={p.onRecord}><Mic size={16} /><span>Record</span></button><button className="mp-button mp-button-secondary" onClick={p.onUpload}><Upload size={15} /><span>Upload</span></button><button className="mp-button mp-button-primary" onClick={p.onJoinMeeting}><Plus size={16} /><span>Join meeting</span></button></div></header>
      {p.workspace.is_demo && <div className="mp-demo-notice"><Radio size={14} />You’re exploring sample data.<button onClick={p.onCreateWorkspace}>Create your workspace <ArrowUpRight size={13} /></button></div>}
      {p.children}
      <footer className="mp-app-footer"><span>MeetPilot · {p.workspace.name}</span><button onClick={p.onHome}>Product home <ArrowUpRight size={12} /></button></footer>
    </div>
  </div>;
}
