import React, { useState } from 'react';
import { AlertCircle, RefreshCw, Upload, Trash2, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';

interface MeetingErrorCardProps {
  meetingId: string;
  meetingTitle: string;
  failureReason?: string | null;
  onRetry: () => Promise<void>;
  onOpenUpload: () => void;
  onDelete: () => void;
}

export const MeetingErrorCard: React.FC<MeetingErrorCardProps> = ({
  meetingTitle,
  failureReason,
  onRetry,
  onOpenUpload,
  onDelete,
}) => {
  const [isRetrying, setIsRetrying] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const handleRetryClick = async () => {
    setIsRetrying(true);
    try {
      await onRetry();
    } finally {
      setIsRetrying(false);
    }
  };

  const cleanErrorMsg = failureReason
    ? failureReason.replace(/Traceback \(most recent call last\):[\s\S]*/, '').trim() || failureReason
    : 'Inference pipeline encountered an unexpected timeout or resource limit. You can retry with a single click.';

  return (
    <div className="p-8 sm:p-10 rounded-2xl bg-rose-950/20 border border-rose-500/30 text-center space-y-6 shadow-2xl animate-fadeIn">
      {/* Icon + Title */}
      <div className="space-y-2">
        <div className="w-14 h-14 rounded-2xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400 mx-auto shadow-lg shadow-rose-950/40">
          <AlertCircle className="w-7 h-7" />
        </div>

        <h2 className="text-xl font-bold text-white tracking-tight">
          Meeting Processing Encountered an Issue
        </h2>

        <p className="text-xs text-rose-300 max-w-md mx-auto leading-relaxed">
          {cleanErrorMsg}
        </p>
      </div>

      {/* Technical Details Accordion */}
      {failureReason && (
        <div className="max-w-lg mx-auto">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-[11px] font-mono text-slate-400 hover:text-slate-200 flex items-center justify-center gap-1 mx-auto"
          >
            <span>{showDetails ? 'Hide technical log' : 'Show technical log'}</span>
            {showDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          {showDetails && (
            <pre className="mt-2 p-3 rounded-xl bg-[#111113] border border-rose-500/20 text-[10px] font-mono text-rose-300 text-left overflow-x-auto max-h-40 scrollbar-thin">
              {failureReason}
            </pre>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap justify-center items-center gap-3 pt-2">
        <button
          onClick={handleRetryClick}
          disabled={isRetrying}
          className="px-5 py-2.5 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] disabled:opacity-40 text-white text-xs font-bold shadow-lg shadow-[#8B5CF6]/25 flex items-center gap-2 cursor-pointer transition-all active:scale-95"
        >
          {isRetrying ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          <span>Retry Processing</span>
        </button>

        <button
          onClick={onOpenUpload}
          className="px-4 py-2.5 rounded-xl bg-[#18181b] hover:bg-[#27272A] border border-[#27272A] text-slate-300 text-xs font-bold transition-colors cursor-pointer flex items-center gap-1.5"
        >
          <Upload className="w-3.5 h-3.5 text-[#8B5CF6]" />
          <span>Re-upload Audio</span>
        </button>

        <button
          onClick={onDelete}
          className="px-4 py-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-bold transition-colors cursor-pointer flex items-center gap-1.5"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>Delete Meeting</span>
        </button>
      </div>
    </div>
  );
};
