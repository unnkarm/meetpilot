import React from 'react';
import { RefreshCw, CheckCircle2, Clock, Loader2 } from 'lucide-react';
import { MeetingStatus } from '../../types';

interface ProcessingStateCardProps {
  status: MeetingStatus;
  meetingTitle: string;
  retryAvailable?: boolean;
  onRetry?: () => Promise<void>;
}

export const ProcessingStateCard: React.FC<ProcessingStateCardProps> = ({
  status,
  meetingTitle,
  retryAvailable,
  onRetry,
}) => {
  const stages = [
    { label: 'Queued for worker', status: 'queued' },
    { label: 'Transcribing audio', status: 'transcribing' },
    { label: 'Indexing transcript', status: 'embedding' },
    { label: 'Extracting summary, tasks and decisions', status: 'analyzing' },
  ] as const;
  const active = status === 'processing' ? 1 : status === 'transcribed' ? 2 : Math.max(0, stages.findIndex((stage) => stage.status === status));

  return (
    <div className="p-8 sm:p-10 rounded-2xl bg-[#111113] border border-[#8B5CF6]/30 shadow-2xl space-y-6 animate-fadeIn text-center">
      {/* Icon & Title */}
      <div className="space-y-3">
        <div className="w-16 h-16 rounded-2xl bg-[#8B5CF6]/15 border border-[#8B5CF6]/30 flex items-center justify-center text-[#8B5CF6] mx-auto shadow-lg shadow-[#8B5CF6]/20">
          <RefreshCw className="w-8 h-8 animate-spin" />
        </div>

        <h2 className="text-xl font-bold text-white tracking-tight">
          {stages[active].label}: {meetingTitle}
        </h2>

        <p className="text-xs text-slate-400 max-w-lg mx-auto leading-relaxed">
          Your recording is safe. This page updates as each processing step finishes.
        </p>
      </div>

      {/* Progress Steps Indicator */}
      <div className="max-w-md mx-auto p-4 rounded-xl bg-[#18181b] border border-[#27272A] space-y-3 text-left">
        {stages.map((stage, index) => (
          <div key={stage.status} className="flex items-center justify-between text-xs text-slate-300">
            <span className="flex items-center gap-2">
              {index < active ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> :
               index === active ? <Loader2 className="w-4 h-4 text-[#8B5CF6] animate-spin" /> :
               <Clock className="w-4 h-4 text-slate-600" />}
              <span>{stage.label}</span>
            </span>
            <span className="text-[10px] font-mono text-slate-400 font-bold">
              {index < active ? 'DONE' : index === active ? 'RUNNING' : 'PENDING'}
            </span>
          </div>
        ))}
      </div>

      {/* Live Polling Status Tag */}
      <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#8B5CF6]/10 border border-[#8B5CF6]/20 text-[#8B5CF6] text-xs font-mono font-semibold">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        <span>Polling pipeline status every 3s...</span>
      </div>
      {retryAvailable && onRetry && (
        <div className="space-y-2">
          <p className="text-xs text-amber-300">This stage has taken longer than expected.</p>
          <button type="button" onClick={onRetry} className="px-4 py-2 rounded-lg bg-[#8B5CF6] text-white text-xs font-bold">Retry processing</button>
        </div>
      )}
    </div>
  );
};
