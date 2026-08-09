import React, { useState } from 'react';
import {
  Video,
  ShieldAlert,
  Bot,
  AlertTriangle,
  CheckCircle2,
  X,
  ExternalLink,
  Sparkles,
  Lock,
} from 'lucide-react';
import { startLiveMeeting } from '../services/api';
import { ApiMeetingDetail } from '../types';

interface LiveMeetingModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId: string;
  getToken?: () => Promise<string | null>;
  onSuccess: (meeting: ApiMeetingDetail) => void;
}

export const LiveMeetingModal: React.FC<LiveMeetingModalProps> = ({
  isOpen,
  onClose,
  workspaceId,
  getToken,
  onSuccess,
}) => {
  const [meetingUrl, setMeetingUrl] = useState('');
  const [meetingTitle, setMeetingTitle] = useState('');
  const [hasLegalConsent, setHasLegalConsent] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasLegalConsent || !meetingUrl.trim()) return;

    setIsLoading(true);
    setErrorMsg(null);

    try {
      const res = await startLiveMeeting(
        workspaceId,
        meetingUrl.trim(),
        meetingTitle.trim() || undefined,
        getToken
      );
      setMeetingUrl('');
      setMeetingTitle('');
      setHasLegalConsent(false);
      onSuccess(res);
      onClose();
    } catch (err: any) {
      console.error('Failed to dispatch live meeting bot:', err);
      setErrorMsg(err.message || 'Failed to dispatch AI meeting capture bot. Please check your link.');
    } finally {
      setIsLoading(false);
    }
  };

  const isFormValid = hasLegalConsent && meetingUrl.trim().length > 3 && !isLoading;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-lg overflow-hidden border rounded-2xl bg-slate-900/95 border-slate-700/70 shadow-2xl shadow-indigo-500/10">
        {/* Glow accent */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-indigo-500 to-cyan-400" />

        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shadow-inner">
              <Video className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                Join Live Google Meet
                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-semibold tracking-wider text-emerald-400 uppercase bg-emerald-950/60 border border-emerald-500/30 rounded-full animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  Self-Hosted Vexa
                </span>
              </h2>
              <p className="text-xs text-slate-400">Dispatch an autonomous AI bot for real-time transcription</p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {errorMsg && (
            <div className="p-3 text-xs text-rose-300 bg-rose-950/40 border border-rose-800/60 rounded-xl flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Meeting URL Input */}
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-slate-300">
              Google Meet Link or Code <span className="text-rose-400">*</span>
            </label>
            <div className="relative">
              <input
                type="text"
                value={meetingUrl}
                onChange={(e) => setMeetingUrl(e.target.value)}
                placeholder="https://meet.google.com/abc-defg-hij or abc-defg-hij"
                required
                className="w-full px-3.5 py-2.5 text-sm text-white bg-slate-950/60 border border-slate-700/80 rounded-xl placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all font-mono"
              />
              <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none text-slate-500 text-xs">
                Google Meet
              </div>
            </div>
            <p className="text-[11px] text-slate-400">
              Paste the full invitation link or the 10-character Google Meet room code.
            </p>
          </div>

          {/* Optional Title Input */}
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-slate-300">
              Session Title <span className="text-slate-500 font-normal">(Optional)</span>
            </label>
            <input
              type="text"
              value={meetingTitle}
              onChange={(e) => setMeetingTitle(e.target.value)}
              placeholder="e.g., Weekly Engineering Sync & Sprint Planning"
              className="w-full px-3.5 py-2.5 text-sm text-white bg-slate-950/60 border border-slate-700/80 rounded-xl placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
            />
          </div>

          {/* STEP C3: Mandatory Legal Consent Disclosure Modal */}
          <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-950/20 space-y-3">
            <div className="flex items-start gap-2.5">
              <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-xs font-semibold text-amber-300 uppercase tracking-wide">
                  Mandatory Legal Consent Disclosure
                </h4>
                <p className="text-xs leading-relaxed text-amber-200/90">
                  You are about to dispatch an AI bot into a Google Meet call. In many jurisdictions, recording or
                  transcribing without the consent of all participants is illegal. Ensure you have informed all
                  participants and have their explicit consent before continuing.
                </p>
              </div>
            </div>

            {/* Mandatory Checkbox */}
            <label className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-950/60 border border-amber-500/20 hover:border-amber-500/40 cursor-pointer transition-colors group">
              <input
                type="checkbox"
                checked={hasLegalConsent}
                onChange={(e) => setHasLegalConsent(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-slate-900 accent-indigo-500 shrink-0 cursor-pointer"
              />
              <span className="text-xs text-slate-200 group-hover:text-white transition-colors select-none font-medium">
                I confirm all participants have been informed and have consented to being recorded/transcribed.
              </span>
            </label>
          </div>

          {/* Bot Features Indicator */}
          <div className="flex items-center justify-between px-3.5 py-2.5 text-xs text-slate-400 rounded-xl bg-slate-950/40 border border-slate-800/80">
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4 text-cyan-400" />
              <span>Real-time WebSocket transcript streaming</span>
            </div>
            <div className="flex items-center gap-1 text-slate-500">
              <Lock className="w-3.5 h-3.5" />
              <span>Workspace-isolated</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2.5 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/60 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!isFormValid}
              className={`flex items-center gap-2 px-5 py-2.5 text-xs font-semibold text-white rounded-xl transition-all shadow-lg ${
                isFormValid
                  ? 'bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 shadow-emerald-500/20 active:scale-[0.98]'
                  : 'bg-slate-800 text-slate-500 border border-slate-700/50 cursor-not-allowed shadow-none'
              }`}
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Dispatching Bot...</span>
                </>
              ) : (
                <>
                  <Bot className="w-4 h-4" />
                  <span>Dispatch Bot & Join Call</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
