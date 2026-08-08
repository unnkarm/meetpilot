import React, { useState } from 'react';
import { Meeting, TaskItem } from '../types';
import { Home, Calendar, CheckSquare, Search, Settings, FileText, Mic, MessageSquare, Sparkles, Clock, CheckCircle2, ChevronRight, Send, AlertCircle, Plus, User } from 'lucide-react';

const SHOWCASE_PREVIEW_MEETINGS: Meeting[] = [
  {
    id: 'sprint-planning',
    workspaceId: 'demo',
    title: 'Weekly Sprint Planning',
    status: 'completed',
    date: 'Today, 10:00 AM',
    duration: '45 mins',
    participants: [
      { name: 'Sarah Chen', avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150', role: 'Lead Architect' },
      { name: 'Alex Rivera', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150', role: 'Product Manager' },
      { name: 'Elena Rostova', avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150', role: 'Frontend Eng' },
    ],
    summary: {
      overview: 'The team aligned on the Q3 Auth Refactor sprint goals, API rate-limiting updates, and micro-frontend transition timeline. Sarah will lead OAuth token security, while Alex finalizes customer migration specs.',
      keyTakeaways: [
        'Auth service migration shifted to modern OAuth 2.1 PKCE standards to mitigate legacy session vulnerabilities.',
        'Redis caching cluster will be upgraded to support sub-5ms transcript index lookups.',
        'Weekly release candidate scheduled for Thursday evening with fallback rollback automation.'
      ],
      nextSteps: [
        'Sarah to complete OAuth 2.1 migration blueprint by Friday 5 PM.',
        'Elena to implement responsive Meeting Memory canvas components.'
      ]
    },
    tasks: [
      {
        id: 't-1',
        title: 'Complete OAuth 2.1 authentication flow implementation',
        assignee: { name: 'Sarah Chen', avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150', role: 'Lead Architect' },
        dueDate: 'This Friday',
        completed: false,
        timestamp: '18:24',
        priority: 'high',
        status: 'todo'
      },
      {
        id: 't-2',
        title: 'Configure Redis cluster rate-limiting for transcript search API',
        assignee: { name: 'Marcus Vance', avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150', role: 'DevOps Lead' },
        dueDate: 'Next Monday',
        completed: true,
        timestamp: '24:10',
        priority: 'medium',
        status: 'done'
      }
    ],
    decisions: [
      {
        id: 'd-1',
        topic: 'Authentication Standard',
        outcome: 'Migrate legacy JWT refresh flow to OAuth 2.1 PKCE with secure HttpOnly cookies.',
        timestamp: '18:10'
      }
    ],
    transcript: [
      { id: 'tr-1', speaker: 'Alex Rivera', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150', time: '00:15', startTime: 15, endTime: 30, text: 'Good morning everyone! Let’s jump straight into the sprint scope for authentication and transcript index performance.' },
      { id: 'tr-2', speaker: 'Sarah Chen', avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150', time: '03:40', startTime: 220, endTime: 245, text: 'I completed the audit of our auth service. We should deprecate custom JWT refresh tokens in favor of OAuth 2.1 standard PKCE.' }
    ]
  },
  {
    id: 'product-review',
    workspaceId: 'demo',
    title: 'Product Strategy & Roadmap Review',
    status: 'completed',
    date: 'Yesterday, 2:30 PM',
    duration: '30 mins',
    participants: [
      { name: 'Alex Rivera', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150', role: 'Product Manager' },
      { name: 'Jessica Taylor', avatar: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150', role: 'Head of Design' }
    ],
    summary: {
      overview: 'Reviewed enterprise customer feedback for MeetPilot AI dashboard. Consensus reached to streamline meeting card metrics, add instant PDF export, and introduce dark mode workspace toggles.',
      keyTakeaways: [
        '92% of users requested one-click action item export to Linear and Jira.',
        'Design team finalized the dark glassmorphic UI system inspired by Linear and Vercel.'
      ],
      nextSteps: ['Jessica to deliver dark UI component library by Friday.']
    },
    tasks: [
      {
        id: 't-3',
        title: 'Export design system tokens for dark luxury theme',
        assignee: { name: 'Jessica Taylor', avatar: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150', role: 'Head of Design' },
        dueDate: 'Friday',
        completed: true,
        timestamp: '14:20',
        priority: 'high',
        status: 'done'
      }
    ],
    decisions: [
      {
        id: 'd-2',
        topic: 'Integrations Focus',
        outcome: 'Prioritize Linear and Notion exports before Slack digest integrations.',
        timestamp: '11:15'
      }
    ],
    transcript: [
      { id: 'tr-3', speaker: 'Jessica Taylor', avatar: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150', time: '02:10', startTime: 130, endTime: 155, text: 'Our core design philosophy is total clarity: minimal noise, high visual contrast, and lightning fast navigation.' }
    ]
  }
];

export const DashboardPreview: React.FC = () => {
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting>(SHOWCASE_PREVIEW_MEETINGS[0]);
  const [activeTab, setActiveTab] = useState<'summary' | 'tasks' | 'transcript' | 'chat'>('summary');
  const [sidebarNav, setSidebarNav] = useState<'home' | 'meetings' | 'tasks' | 'search' | 'settings'>('meetings');

  // Dynamic preview tasks
  const [previewTasks, setPreviewTasks] = useState<Record<string, TaskItem[]>>(() => {
    const initial: Record<string, TaskItem[]> = {};
    SHOWCASE_PREVIEW_MEETINGS.forEach((m) => {
      initial[m.id] = [...m.tasks];
    });
    return initial;
  });


  const [previewQuickTitle, setPreviewQuickTitle] = useState('');
  const [previewQuickAssignee, setPreviewQuickAssignee] = useState('Sarah Chen');

  const handlePreviewQuickAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!previewQuickTitle.trim()) return;

    const newTask: TaskItem = {
      id: `p-task-${Date.now()}`,
      title: previewQuickTitle.trim(),
      assignee: {
        name: previewQuickAssignee,
        role: 'Teammate',
        avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150'
      },
      dueDate: 'This Week',
      completed: false,
      timestamp: 'Just now',
      priority: 'high',
      status: 'todo'
    };

    setPreviewTasks(prev => ({
      ...prev,
      [selectedMeeting.id]: [...(prev[selectedMeeting.id] || []), newTask]
    }));

    setPreviewQuickTitle('');
  };

  const upcomingDeadlines = [
    { day: 'Friday', task: 'Authentication Refactor (OAuth 2.1)', owner: 'Sarah Chen', status: 'In Progress', color: 'text-amber-400' },
    { day: 'Monday', task: 'Cloud SQL Read Replicas Deployment', owner: 'David Kim', status: 'Pending', color: 'text-blue-400' },
    { day: 'Wednesday', task: 'TestFlight Mobile App Design Review', owner: 'Elena Rostova', status: 'Scheduled', color: 'text-purple-400' }
  ];

  return (
    <section id="dashboard-preview" className="py-20 lg:py-28 relative overflow-hidden bg-[#09090B] border-t border-[#27272A]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 space-y-10">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#111113] border border-[#27272A] text-[#8B5CF6] text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-[#8B5CF6]" />
            <span>Linear & Notion Hybrid Workspace</span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-extrabold text-[#FAFAFA] tracking-tight">
            The AI Workspace for Product Teams
          </h2>

          <p className="text-slate-400 text-base sm:text-lg">
            A unified execution hub connecting transcripts, task lists, and upcoming deadlines.
          </p>
        </div>

        {/* 3-Panel Workspace Container */}
        <div className="rounded-2xl bg-[#111113] border border-[#27272A] shadow-2xl overflow-hidden grid grid-cols-1 lg:grid-cols-12 min-h-[620px]">
          
          {/* PANEL 1: LEFT SIDEBAR NAVIGATION (Col Span 3) */}
          <div className="lg:col-span-3 border-r border-[#27272A] bg-[#09090B] p-4 flex flex-col justify-between">
            <div className="space-y-6">
              
              {/* Brand Header */}
              <div className="flex items-center gap-2 px-2 pt-1">
                <div className="w-6 h-6 rounded-lg bg-[#8B5CF6] flex items-center justify-center font-bold text-white text-xs">
                  M
                </div>
                <span className="font-bold text-sm text-[#FAFAFA]">MeetPilot AI</span>
              </div>

              {/* Navigation Options */}
              <nav className="space-y-1 font-medium text-xs">
                <button
                  onClick={() => setSidebarNav('home')}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl transition-colors cursor-pointer ${
                    sidebarNav === 'home' ? 'bg-[#18181b] text-white font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Home className="w-4 h-4 text-slate-400" />
                  <span>Home</span>
                </button>

                <button
                  onClick={() => setSidebarNav('meetings')}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-xl transition-colors cursor-pointer ${
                    sidebarNav === 'meetings' ? 'bg-[#18181b] text-[#8B5CF6] font-bold border border-[#8B5CF6]/30' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Calendar className="w-4 h-4 text-[#8B5CF6]" />
                    <span>Meetings</span>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#8B5CF6]/20 text-[#8B5CF6]">3</span>
                </button>

                <button
                  onClick={() => setSidebarNav('tasks')}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl transition-colors cursor-pointer ${
                    sidebarNav === 'tasks' ? 'bg-[#18181b] text-white font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <CheckSquare className="w-4 h-4 text-emerald-400" />
                  <span>Tasks</span>
                </button>

                <button
                  onClick={() => setSidebarNav('search')}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl transition-colors cursor-pointer ${
                    sidebarNav === 'search' ? 'bg-[#18181b] text-white font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Search className="w-4 h-4 text-[#3B82F6]" />
                  <span>Search</span>
                </button>

                <button
                  onClick={() => setSidebarNav('settings')}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl transition-colors cursor-pointer ${
                    sidebarNav === 'settings' ? 'bg-[#18181b] text-white font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Settings className="w-4 h-4 text-slate-500" />
                  <span>Settings</span>
                </button>
              </nav>

              {/* Meetings List */}
              <div className="pt-4 border-t border-[#27272A] space-y-2">
                <div className="text-[10px] font-mono uppercase text-slate-500 px-2">Recent Recordings</div>
                {SHOWCASE_PREVIEW_MEETINGS.slice(0, 3).map((m) => (
                  <div
                    key={m.id}
                    onClick={() => setSelectedMeeting(m)}
                    className={`p-2.5 rounded-xl text-xs cursor-pointer transition-all border ${
                      selectedMeeting.id === m.id
                        ? 'bg-[#18181b] border-[#8B5CF6]/50 text-white font-bold'
                        : 'bg-transparent border-transparent hover:bg-[#18181b] text-slate-400'
                    }`}
                  >
                    <div className="truncate">{m.title}</div>
                    <div className="text-[10px] text-slate-500 mt-0.5">{m.duration} • {m.date}</div>
                  </div>
                ))}
              </div>

            </div>

            <div className="p-2.5 rounded-xl bg-[#18181b] border border-[#27272A] text-[11px] text-slate-400 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Encrypted Workspace</span>
            </div>
          </div>

          {/* PANEL 2: MIDDLE MAIN WORKSPACE (Col Span 6) */}
          <div className="lg:col-span-6 p-6 space-y-6 flex flex-col justify-between">
            
            {/* Header + Tabs */}
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#27272A]">
                <div>
                  <h3 className="text-lg font-bold text-[#FAFAFA]">{selectedMeeting.title}</h3>
                  <div className="text-xs text-slate-500">{selectedMeeting.date} • {selectedMeeting.duration}</div>
                </div>

                <div className="flex items-center gap-1 bg-[#18181b] p-1 rounded-xl border border-[#27272A]">
                  <button
                    onClick={() => setActiveTab('summary')}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                      activeTab === 'summary' ? 'bg-[#8B5CF6] text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Summary
                  </button>
                  <button
                    onClick={() => setActiveTab('tasks')}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                      activeTab === 'tasks' ? 'bg-[#8B5CF6] text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Tasks ({selectedMeeting.tasks.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('transcript')}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                      activeTab === 'transcript' ? 'bg-[#8B5CF6] text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Transcript
                  </button>
                  <button
                    onClick={() => setActiveTab('chat')}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                      activeTab === 'chat' ? 'bg-[#8B5CF6] text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Chat
                  </button>
                </div>
              </div>

              {/* Tab Display Content */}
              {activeTab === 'summary' && (
                <div className="space-y-4 text-xs text-slate-300">
                  <div className="p-4 rounded-xl bg-[#18181b] border border-[#27272A]">
                    <div className="font-bold text-[#FAFAFA] mb-1">Executive Overview</div>
                    <p className="leading-relaxed">{selectedMeeting.summary.overview}</p>
                  </div>

                  <div className="space-y-2">
                    <div className="font-mono text-slate-500 text-[10px] uppercase">Key Decisions</div>
                    {selectedMeeting.summary.keyTakeaways.map((takeaway, idx) => (
                      <div key={idx} className="p-3 rounded-lg bg-[#18181b] border border-[#27272A] flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{takeaway}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === 'tasks' && (
                <div className="space-y-3 text-xs">
                  <div className="space-y-2">
                    {(previewTasks[selectedMeeting.id] || selectedMeeting.tasks).map((task) => (
                      <div key={task.id} className="p-3.5 rounded-xl bg-[#18181b] border border-[#27272A] flex items-center justify-between">
                        <div>
                          <div className="font-bold text-[#FAFAFA]">{task.title}</div>
                          <div className="text-slate-500 mt-1">Assignee: {task.assignee.name} • Due: {task.dueDate}</div>
                        </div>
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono text-[10px]">
                          @{task.timestamp}
                        </span>
                      </div>
                    ))}
                  </div>

                  <form onSubmit={handlePreviewQuickAdd} className="p-3 rounded-xl bg-[#18181b] border border-[#8B5CF6]/40 flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="Quick add task and assign..."
                      value={previewQuickTitle}
                      onChange={(e) => setPreviewQuickTitle(e.target.value)}
                      className="flex-1 bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none"
                    />
                    <select
                      value={previewQuickAssignee}
                      onChange={(e) => setPreviewQuickAssignee(e.target.value)}
                      className="bg-[#111113] border border-[#27272A] rounded-lg px-2 py-1 text-[11px] text-slate-300 focus:outline-none"
                    >
                      <option value="Sarah Chen">Sarah Chen</option>
                      <option value="Marcus Vance">Marcus Vance</option>
                      <option value="Elena Rostova">Elena Rostova</option>
                      <option value="Alex Rivera">Alex Rivera</option>
                    </select>
                    <button
                      type="submit"
                      disabled={!previewQuickTitle.trim()}
                      className="px-3 py-1 rounded-lg bg-[#8B5CF6] hover:bg-[#7c3aed] disabled:opacity-40 text-white font-bold text-xs cursor-pointer flex items-center gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add</span>
                    </button>
                  </form>
                </div>
              )}

              {activeTab === 'transcript' && (
                <div className="space-y-2 text-xs">
                  {selectedMeeting.transcript.map((line) => (
                    <div key={line.id} className="p-3 rounded-xl bg-[#18181b] border border-[#27272A] space-y-1">
                      <div className="flex items-center justify-between text-[#8B5CF6] font-bold">
                        <span>{line.speaker}</span>
                        <span className="font-mono text-[10px] text-slate-500">@{line.time}</span>
                      </div>
                      <p className="text-slate-300">{line.text}</p>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === 'chat' && (
                <div className="space-y-3 text-xs">
                  <div className="p-4 rounded-xl bg-[#18181b] border border-[#8B5CF6]/40 space-y-2">
                    <div className="font-bold text-[#8B5CF6] flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" /> AI Assistant
                    </div>
                    <p className="text-slate-200">
                      Sarah Chen is assigned to authentication. Her deadline is Friday at 5 PM.
                    </p>
                  </div>
                </div>
              )}

            </div>

            <div className="pt-3 border-t border-[#27272A] flex items-center gap-2">
              <input
                type="text"
                placeholder="Type to filter workspace or ask AI..."
                className="w-full bg-[#18181b] border border-[#27272A] rounded-xl px-3.5 py-2 text-xs text-[#FAFAFA] focus:outline-none focus:border-[#8B5CF6]"
              />
            </div>

          </div>

          {/* PANEL 3: RIGHT PANEL WITH UPCOMING DEADLINES (Col Span 3) */}
          <div className="lg:col-span-3 border-l border-[#27272A] bg-[#09090B] p-5 space-y-6">
            
            <div className="flex items-center justify-between pb-3 border-b border-[#27272A]">
              <h4 className="text-xs font-mono uppercase font-bold text-slate-400">Upcoming Deadlines</h4>
              <Clock className="w-3.5 h-3.5 text-[#8B5CF6]" />
            </div>

            <div className="space-y-3">
              {upcomingDeadlines.map((item, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-[#18181b] border border-[#27272A] space-y-2 hover:border-[#8B5CF6]/30 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className={`text-xs font-bold font-mono ${item.color}`}>{item.day}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-slate-400 font-mono">
                      {item.status}
                    </span>
                  </div>

                  <p className="text-xs font-bold text-[#FAFAFA] leading-snug">
                    {item.task}
                  </p>

                  <div className="text-[11px] text-slate-500 font-medium">
                    Owner: <span className="text-slate-300">{item.owner}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="p-3 rounded-xl bg-gradient-to-r from-[#8B5CF6]/20 to-[#3B82F6]/10 border border-[#8B5CF6]/30 text-xs text-slate-300 space-y-1">
              <div className="font-bold text-[#FAFAFA] flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5 text-[#8B5CF6]" /> Auto-Sync Active
              </div>
              <p className="text-[11px] text-slate-400">
                All deadlines are synced bi-directionally with Linear and Slack channels.
              </p>
            </div>

          </div>

        </div>

      </div>
    </section>
  );
};

