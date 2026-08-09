import React, { useState } from 'react';
import {
  Calendar,
  Clock,
  Edit3,
  Check,
  X,
  Trash2,
  Radio,
  Volume2,
  Users,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { ApiMeetingDetail, ApiMeetingListItem, MeetingStatus } from '../../types';
import { ExportDropdown } from './ExportDropdown';
import { MeetingSpeakerStats } from '../../utils/speakerUtils';

interface MeetingHeaderProps {
  meeting: ApiMeetingDetail;
  allMeetings: ApiMeetingListItem[];
  speakerStats: MeetingSpeakerStats;
  onSelectMeeting: (meetingId: string) => void;
  onRenameMeeting: (newTitle: string) => Promise<void>;
  onDeleteMeeting: (meetingId: string, title: string) => void;
  onExportMarkdown: () => void;
  onExportJSON: () => void;
  onExportPDF: () => void;
}

const STATUS_CONFIG: Record<
  MeetingStatus,
  { label: string; bg: string; text: string; border: string; icon: React.ReactNode }
> = {
  completed: {
    label: 'Completed',
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    border: 'border-emerald-500/30',
    icon: <CheckCircle2 className="w-3.5 h-3.5" />,
  },
  processing: {
    label: 'Processing',
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    border: 'border-amber-500/30',
    icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
  },
  queued: {
    label: 'Queued',
    bg: 'bg-blue-500/10',
    text: 'text-blue-400',
    border: 'border-blue-500/30',
    icon: <Clock className="w-3.5 h-3.5" />,
  },
  failed: {
    label: 'Failed',
    bg: 'bg-rose-500/10',
    text: 'text-rose-400',
    border: 'border-rose-500/30',
    icon: <AlertCircle className="w-3.5 h-3.5" />,
  },
  in_progress: {
    label: 'Live Active',
    bg: 'bg-purple-500/10',
    text: 'text-purple-400',
    border: 'border-purple-500/30',
    icon: <Radio className="w-3.5 h-3.5 animate-pulse" />,
  },
};

export const MeetingHeader: React.FC<MeetingHeaderProps> = ({
  meeting,
  allMeetings,
  speakerStats,
  onSelectMeeting,
  onRenameMeeting,
  onDeleteMeeting,
  onExportMarkdown,
  onExportJSON,
  onExportPDF,
}) => {
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleInput, setTitleInput] = useState(meeting.title);
  const [savingTitle, setSavingTitle] = useState(false);

  const statusInfo = STATUS_CONFIG[meeting.status] || STATUS_CONFIG.completed;

  const handleSaveTitle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!titleInput.trim() || titleInput.trim() === meeting.title) {
      setIsEditingTitle(false);
      return;
    }
    setSavingTitle(true);
    try {
      await onRenameMeeting(titleInput.trim());
      setIsEditingTitle(false);
    } finally {
      setSavingTitle(false);
    }
  };

  const formattedDate = meeting.created_at
    ? new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }).format(new Date(meeting.created_at))
    : 'Recently';

  const durationMin = meeting.duration_seconds
    ? `${Math.max(1, Math.round(meeting.duration_seconds / 60))} mins`
    : '< 1 min';

  return (
    <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4 shadow-xl">
      {/* Top Row: Title + Status + Action Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left Side: Title & Status */}
        <div className="space-y-1.5 flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            {isEditingTitle ? (
              <form onSubmit={handleSaveTitle} className="flex items-center gap-2">
                <input
                  type="text"
                  value={titleInput}
                  onChange={(e) => setTitleInput(e.target.value)}
                  autoFocus
                  className="bg-[#18181b] border border-[#8B5CF6] rounded-xl px-3 py-1 text-base sm:text-lg font-bold text-white focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={savingTitle}
                  className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors"
                >
                  <Check className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setTitleInput(meeting.title);
                    setIsEditingTitle(false);
                  }}
                  className="p-1.5 rounded-lg bg-[#27272A] text-slate-400 hover:text-white transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </form>
            ) : (
              <div className="flex items-center gap-2.5 max-w-full">
                <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight truncate">
                  {meeting.title}
                </h1>
                <button
                  onClick={() => {
                    setTitleInput(meeting.title);
                    setIsEditingTitle(true);
                  }}
                  title="Rename Meeting"
                  className="p-1 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-[#18181b] transition-colors cursor-pointer shrink-0"
                >
                  <Edit3 className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Semantic Status Badge */}
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold border ${statusInfo.bg} ${statusInfo.text} ${statusInfo.border}`}
            >
              {statusInfo.icon}
              <span>{statusInfo.label.toUpperCase()}</span>
            </span>
          </div>

          {/* Secondary Metadata Strip */}
          <div className="flex items-center gap-3 text-xs text-slate-400 flex-wrap font-medium">
            <span className="flex items-center gap-1 text-slate-300">
              <Calendar className="w-3.5 h-3.5 text-[#8B5CF6]" />
              <span>{formattedDate}</span>
            </span>
            <span className="text-slate-600">•</span>
            <span className="flex items-center gap-1 text-slate-300">
              <Clock className="w-3.5 h-3.5 text-[#8B5CF6]" />
              <span>{durationMin}</span>
            </span>
            <span className="text-slate-600">•</span>
            <span className="flex items-center gap-1 text-slate-300">
              <Users className="w-3.5 h-3.5 text-[#8B5CF6]" />
              <span>{speakerStats.displayLabel}</span>
            </span>
            <span className="text-slate-600">•</span>
            <span className="flex items-center gap-1 text-slate-400">
              {meeting.source === 'live' ? (
                <>
                  <Radio className="w-3.5 h-3.5 text-purple-400" />
                  <span>Google Meet Live Bot</span>
                </>
              ) : (
                <>
                  <Volume2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Audio Ingestion</span>
                </>
              )}
            </span>
          </div>
        </div>

        {/* Right Side: Meeting Switcher + Export Dropdown + Delete */}
        <div className="flex items-center gap-2.5 shrink-0">
          {/* Meeting Selector */}
          {allMeetings.length > 1 && (
            <select
              value={meeting.id}
              onChange={(e) => onSelectMeeting(e.target.value)}
              className="bg-[#18181b] border border-[#27272A] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-[#8B5CF6] cursor-pointer"
            >
              {allMeetings.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.title} ({m.status})
                </option>
              ))}
            </select>
          )}

          {/* Export Dropdown */}
          {meeting.status === 'completed' && (
            <ExportDropdown
              onExportMarkdown={onExportMarkdown}
              onExportJSON={onExportJSON}
              onExportPDF={onExportPDF}
            />
          )}

          {/* Delete Meeting */}
          <button
            onClick={() => onDeleteMeeting(meeting.id, meeting.title)}
            title={`Delete ${meeting.title}`}
            className="p-2 rounded-xl bg-[#18181b] hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 border border-[#27272A] transition-colors cursor-pointer"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
