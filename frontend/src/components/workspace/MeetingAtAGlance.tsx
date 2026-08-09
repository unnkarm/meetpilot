import React from 'react';
import { Clock, Users, CheckSquare, Sparkles } from 'lucide-react';
import { MeetingSpeakerStats } from '../../utils/speakerUtils';

interface MeetingAtAGlanceProps {
  durationSeconds?: number | null;
  speakerStats: MeetingSpeakerStats;
  decisionsCount: number;
  tasksCount: number;
  completedTasksCount?: number;
}

export const MeetingAtAGlance: React.FC<MeetingAtAGlanceProps> = ({
  durationSeconds,
  speakerStats,
  decisionsCount,
  tasksCount,
  completedTasksCount = 0,
}) => {
  const formatDurationDisplay = (secs?: number | null) => {
    if (!secs || secs <= 0) return '< 1 min';
    if (secs < 60) return `${Math.round(secs)}s`;
    const mins = Math.floor(secs / 60);
    const remainderSecs = Math.round(secs % 60);
    return remainderSecs > 0 ? `${mins}m ${remainderSecs}s` : `${mins} mins`;
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
      {/* 1. Duration */}
      <div className="p-4 rounded-xl bg-[#111113] border border-[#27272A] flex items-center gap-3.5 shadow-sm hover:border-[#8B5CF6]/30 transition-colors">
        <div className="w-10 h-10 rounded-xl bg-[#8B5CF6]/10 border border-[#8B5CF6]/20 flex items-center justify-center text-[#8B5CF6] shrink-0">
          <Clock className="w-5 h-5" />
        </div>
        <div>
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
            Duration
          </div>
          <div className="text-lg font-black text-white">{formatDurationDisplay(durationSeconds)}</div>
          <div className="text-[10px] text-slate-400 font-medium">16kHz audio recording</div>
        </div>
      </div>

      {/* 2. Detected Speakers */}
      <div className="p-4 rounded-xl bg-[#111113] border border-[#27272A] flex items-center gap-3.5 shadow-sm hover:border-cyan-500/30 transition-colors">
        <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
          <Users className="w-5 h-5" />
        </div>
        <div>
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
            Speakers
          </div>
          <div className="text-lg font-black text-white">{speakerStats.detectedCount} Detected</div>
          <div className="text-[10px] text-cyan-400 font-medium">PyAnnote Community-1</div>
        </div>
      </div>

      {/* 3. Consensus Decisions */}
      <div className="p-4 rounded-xl bg-[#111113] border border-[#27272A] flex items-center gap-3.5 shadow-sm hover:border-amber-500/30 transition-colors">
        <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
            Decisions
          </div>
          <div className="text-lg font-black text-white">{decisionsCount} Logged</div>
          <div className="text-[10px] text-amber-400 font-medium">Agreement consensus</div>
        </div>
      </div>

      {/* 4. Action Items */}
      <div className="p-4 rounded-xl bg-[#111113] border border-[#27272A] flex items-center gap-3.5 shadow-sm hover:border-emerald-500/30 transition-colors">
        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
          <CheckSquare className="w-5 h-5" />
        </div>
        <div>
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
            Action Items
          </div>
          <div className="text-lg font-black text-white">{tasksCount} Extracted</div>
          <div className="text-[10px] text-emerald-400 font-medium">
            {completedTasksCount > 0 ? `${completedTasksCount} completed` : 'Kanban synchronized'}
          </div>
        </div>
      </div>
    </div>
  );
};
