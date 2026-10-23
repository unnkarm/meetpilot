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
  canManage?: boolean;
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
    text: 'text-emerald-700',
    border: 'border-emerald-500/30',
    icon: <CheckCircle2 className="w-3.5 h-3.5" />,
  },
  processing: {
    label: 'Processing',
    bg: 'bg-amber-500/10',
    text: 'text-amber-700',
    border: 'border-amber-500/30',
    icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
  },
  transcribing: {
    label: 'Transcribing', bg: 'bg-brand/10', text: 'text-brand',
    border: 'border-brand/30', icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
  },
  transcribed: {
    label: 'Transcript ready', bg: 'bg-brand/10', text: 'text-brand',
    border: 'border-brand/30', icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
  },
  embedding: {
    label: 'Indexing', bg: 'bg-brand/10', text: 'text-brand',
    border: 'border-brand/30', icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
  },
  analyzing: {
    label: 'Analyzing', bg: 'bg-brand/10', text: 'text-brand',
    border: 'border-brand/30', icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
  },
  queued: {
    label: 'Queued',
    bg: 'bg-blue-500/10',
    text: 'text-blue-700',
    border: 'border-blue-500/30',
    icon: <Clock className="w-3.5 h-3.5" />,
  },
  failed: {
    label: 'Failed',
    bg: 'bg-rose-500/10',
    text: 'text-rose-700',
    border: 'border-rose-500/30',
    icon: <AlertCircle className="w-3.5 h-3.5" />,
  },
  in_progress: {
    label: 'Live',
    bg: 'bg-brand/10',
    text: 'text-brand',
    border: 'border-brand/30',
    icon: <Radio className="w-3.5 h-3.5 animate-pulse" />,
  },
};

export const MeetingHeader: React.FC<MeetingHeaderProps> = ({
  canManage = false,
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
    <div className="p-6 rounded-xl bg-surface border border-line space-y-4 shadow-sm">
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
                  className="bg-surface border border-brand rounded-xl px-3 py-1 text-base sm:text-lg font-bold text-ink focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={savingTitle}
                  className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-700 hover:bg-emerald-500/30 transition-colors"
                >
                  <Check className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setTitleInput(meeting.title);
                    setIsEditingTitle(false);
                  }}
                  className="p-1.5 rounded-lg bg-line text-muted hover:text-ink transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </form>
            ) : (
              <div className="flex items-center gap-2.5 max-w-full">
                <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight truncate">
                  {meeting.title}
                </h1>
                <button
                  disabled={!canManage}
                  onClick={() => {
                    setTitleInput(meeting.title);
                    setIsEditingTitle(true);
                  }}
                  title="Rename Meeting"
                  className="p-1 rounded-lg text-muted hover:text-ink hover:bg-surface transition-colors cursor-pointer shrink-0"
                >
                  <Edit3 className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Semantic Status Badge */}
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-mono font-bold border ${statusInfo.bg} ${statusInfo.text} ${statusInfo.border}`}
            >
              {statusInfo.icon}
              <span>{statusInfo.label.toUpperCase()}</span>
            </span>
          </div>

          {/* Secondary Metadata Strip */}
          <div className="flex items-center gap-3 text-sm text-muted flex-wrap font-medium">
            <span className="flex items-center gap-1 text-ink">
              <Calendar className="w-3.5 h-3.5 text-brand" />
              <span>{formattedDate}</span>
            </span>
            <span className="text-slate-600">•</span>
            <span className="flex items-center gap-1 text-ink">
              <Clock className="w-3.5 h-3.5 text-brand" />
              <span>{durationMin}</span>
            </span>
            <span className="text-slate-600">•</span>
            <span className="flex items-center gap-1 text-ink">
              <Users className="w-3.5 h-3.5 text-brand" />
              <span>{speakerStats.displayLabel}</span>
            </span>
            <span className="text-slate-600">•</span>
            <span className="flex items-center gap-1 text-muted">
              {meeting.source === 'live' ? (
                <>
                  <Radio className="w-3.5 h-3.5 text-brand" />
                  <span>Live meeting assistant</span>
                </>
              ) : (
                <>
                  <Volume2 className="w-3.5 h-3.5 text-emerald-700" />
                  <span>Uploaded recording</span>
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
              className="bg-surface border border-line rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:border-brand cursor-pointer"
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
            disabled={!canManage}
            onClick={() => onDeleteMeeting(meeting.id, meeting.title)}
            title={`Delete ${meeting.title}`}
            className="p-2 rounded-xl bg-surface hover:bg-rose-500/20 text-muted hover:text-rose-700 border border-line transition-colors cursor-pointer"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
