import React, { useState } from 'react';
import { AlertCircle, RefreshCw, Upload, Trash2, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';

interface MeetingErrorCardProps {
  canManage?: boolean;
  meetingId: string;
  meetingTitle: string;
  failureReason?: string | null;
  onRetry: () => Promise<void>;
  onOpenUpload: () => void;
  isLive?: boolean;
  onNewLiveMeeting?: () => void;
  onDelete: () => void;
}

export const MeetingErrorCard: React.FC<MeetingErrorCardProps> = ({
  canManage = false,
  meetingTitle,
  failureReason,
  onRetry,
  onOpenUpload,
  isLive,
  onNewLiveMeeting,
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
    <div className="p-8 sm:p-10 rounded-xl bg-rose-50 border border-rose-500/30 text-center space-y-6 shadow-sm animate-fadeIn">
      {/* Icon + Title */}
      <div className="space-y-2">
        <div className="w-14 h-14 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-700 mx-auto shadow-sm ">
          <AlertCircle className="w-7 h-7" />
        </div>

        <h2 className="text-xl font-bold text-ink tracking-tight">
          {isLive ? 'Meeting Bot Could Not Join' : 'Meeting Processing Encountered an Issue'}
        </h2>

        <p className="text-sm text-rose-700 max-w-md mx-auto leading-relaxed">
          {cleanErrorMsg}
        </p>
      </div>

      {/* Technical Details Accordion */}
      {failureReason && (
        <div className="max-w-lg mx-auto">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-sm font-mono text-muted hover:text-ink flex items-center justify-center gap-1 mx-auto"
          >
            <span>{showDetails ? 'Hide technical log' : 'Show technical log'}</span>
            {showDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          {showDetails && (
            <pre className="mt-2 p-3 rounded-xl bg-surface border border-rose-500/20 text-sm font-mono text-rose-700 text-left overflow-x-auto max-h-40 scrollbar-thin">
              {failureReason}
            </pre>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap justify-center items-center gap-3 pt-2">
        {!isLive && <button
          onClick={handleRetryClick}
          disabled={isRetrying || !canManage}
          className="px-5 py-2.5 rounded-xl bg-brand hover:bg-brand disabled:opacity-40 text-on-brand text-sm font-bold shadow-sm  flex items-center gap-2 cursor-pointer transition-all active:scale-95"
        >
          {isRetrying ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          <span>Retry Processing</span>
        </button>}

        {isLive && onNewLiveMeeting && <button
          onClick={onNewLiveMeeting}
          className="px-5 py-2.5 rounded-xl bg-brand hover:bg-brand text-on-brand text-sm font-bold shadow-sm "
        >Start Bot Again</button>}

        {!isLive && <button
          onClick={onOpenUpload}
          className="px-4 py-2.5 rounded-xl bg-surface hover:bg-line border border-line text-ink text-sm font-bold transition-colors cursor-pointer flex items-center gap-1.5"
        >
          <Upload className="w-3.5 h-3.5 text-brand" />
          <span>Re-upload Audio</span>
        </button>}

        <button
          onClick={onDelete}
          disabled={!canManage}
          className="px-4 py-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-700 text-sm font-bold transition-colors cursor-pointer flex items-center gap-1.5"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>Delete Meeting</span>
        </button>
      </div>
    </div>
  );
};
