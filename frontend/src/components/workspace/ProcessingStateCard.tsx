import React from 'react';
import { RefreshCw, CheckCircle2, Clock, Loader2, Sparkles } from 'lucide-react';
import { MeetingStatus } from '../../types';

interface ProcessingStateCardProps {
  status: MeetingStatus;
  meetingTitle: string;
}

export const ProcessingStateCard: React.FC<ProcessingStateCardProps> = ({
  status,
  meetingTitle,
}) => {
  const isQueued = status === 'queued';

  return (
    <div className="p-8 sm:p-10 rounded-2xl bg-[#111113] border border-[#8B5CF6]/30 shadow-2xl space-y-6 animate-fadeIn text-center">
      {/* Icon & Title */}
      <div className="space-y-3">
        <div className="w-16 h-16 rounded-2xl bg-[#8B5CF6]/15 border border-[#8B5CF6]/30 flex items-center justify-center text-[#8B5CF6] mx-auto shadow-lg shadow-[#8B5CF6]/20">
          <RefreshCw className="w-8 h-8 animate-spin" />
        </div>

        <h2 className="text-xl font-bold text-white tracking-tight">
          {isQueued
            ? `Meeting "${meetingTitle}" is Queued`
            : `Processing & Analyzing "${meetingTitle}"`}
        </h2>

        <p className="text-xs text-slate-400 max-w-lg mx-auto leading-relaxed">
          {isQueued
            ? 'The audio file is scheduled in Celery. Automatic polling is active.'
            : 'Speech transcription, speaker diarization, executive summarization, and vector embedding are running in the pipeline.'}
        </p>
      </div>

      {/* Progress Steps Indicator */}
      <div className="max-w-md mx-auto p-4 rounded-xl bg-[#18181b] border border-[#27272A] space-y-3 text-left">
        <div className="flex items-center justify-between text-xs text-slate-300">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Audio Ingested & Normalized</span>
          </span>
          <span className="text-[10px] font-mono text-emerald-400 font-bold">DONE</span>
        </div>

        <div className="flex items-center justify-between text-xs text-slate-300">
          <span className="flex items-center gap-2">
            {isQueued ? (
              <Clock className="w-4 h-4 text-amber-400" />
            ) : (
              <Loader2 className="w-4 h-4 text-[#8B5CF6] animate-spin" />
            )}
            <span>Whisper Speech Transcription & Diarization</span>
          </span>
          <span className="text-[10px] font-mono text-amber-400 font-bold">
            {isQueued ? 'QUEUED' : 'RUNNING'}
          </span>
        </div>

        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-slate-600" />
            <span>Single-Pass Executive Intelligence Extraction</span>
          </span>
          <span className="text-[10px] font-mono text-slate-600 font-bold">PENDING</span>
        </div>
      </div>

      {/* Live Polling Status Tag */}
      <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#8B5CF6]/10 border border-[#8B5CF6]/20 text-[#8B5CF6] text-xs font-mono font-semibold">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        <span>Polling pipeline status every 3s...</span>
      </div>
    </div>
  );
};
