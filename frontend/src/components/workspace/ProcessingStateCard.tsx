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
    <div className="p-8 sm:p-10 rounded-xl bg-surface border border-brand/30 shadow-sm space-y-6 animate-fadeIn text-center">
      {/* Icon & Title */}
      <div className="space-y-3">
        <div className="w-16 h-16 rounded-xl bg-brand/15 border border-brand/30 flex items-center justify-center text-brand mx-auto shadow-sm ">
          <RefreshCw className="w-8 h-8 animate-spin" />
        </div>

        <h2 className="text-xl font-bold text-ink tracking-tight">
          {stages[active].label}: {meetingTitle}
        </h2>

        <p className="text-sm text-muted max-w-lg mx-auto leading-relaxed">
          Your recording is safe. This page updates as each processing step finishes.
        </p>
      </div>

      {/* Progress Steps Indicator */}
      <div className="max-w-md mx-auto p-4 rounded-xl bg-surface border border-line space-y-3 text-left">
        {stages.map((stage, index) => (
          <div key={stage.status} className="flex items-center justify-between text-sm text-ink">
            <span className="flex items-center gap-2">
              {index < active ? <CheckCircle2 className="w-4 h-4 text-emerald-700" /> :
               index === active ? <Loader2 className="w-4 h-4 text-brand animate-spin" /> :
               <Clock className="w-4 h-4 text-slate-600" />}
              <span>{stage.label}</span>
            </span>
            <span className="text-sm font-mono text-muted font-bold">
              {index < active ? 'DONE' : index === active ? 'RUNNING' : 'PENDING'}
            </span>
          </div>
        ))}
      </div>

      {/* Live Polling Status Tag */}
      <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-brand/10 border border-brand/20 text-brand text-sm font-mono font-semibold">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        <span>Polling pipeline status every 3s...</span>
      </div>
      {retryAvailable && onRetry && (
        <div className="space-y-2">
          <p className="text-sm text-amber-700">This stage has taken longer than expected.</p>
          <button type="button" onClick={onRetry} className="px-4 py-2 rounded-lg bg-brand text-on-brand text-sm font-bold">Retry processing</button>
        </div>
      )}
    </div>
  );
};
