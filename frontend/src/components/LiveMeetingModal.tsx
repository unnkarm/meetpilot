import React, { useState, useEffect } from 'react';
import {
  Video,
  ShieldCheck,
  Bot,
  AlertTriangle,
  CheckCircle2,
  X,
  Lock,
  Radio,
  Sparkles,
  ExternalLink,
  Clipboard,
  Check,
  FileText,
  Users,
  Zap,
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
  const [hasCopiedUrl, setHasCopiedUrl] = useState(false);

  // Quick preset titles
  const quickTitles = ['Weekly Sync', 'Sprint Planning', 'Engineering Review', 'Client Call'];

  // Reset state when opening/closing
  useEffect(() => {
    if (!isOpen) {
      setErrorMsg(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // Validate Google Meet URL/code format
  const cleanUrl = meetingUrl.trim();
  const isMeetCodeOrUrl =
    cleanUrl.length > 0 &&
    (cleanUrl.includes('meet.google.com/') ||
      /^[a-z]{3}-[a-z]{4}-[a-z]{3}$/i.test(cleanUrl) ||
      cleanUrl.length >= 8);

  const isFormValid = hasLegalConsent && isMeetCodeOrUrl && !isLoading;

  const handlePasteClipboard = async () => {
    try {
      if (navigator?.clipboard?.readText) {
        const text = await navigator.clipboard.readText();
        if (text) {
          setMeetingUrl(text.trim());
          setHasCopiedUrl(true);
          setTimeout(() => setHasCopiedUrl(false), 2000);
        }
      }
    } catch {
      // Clipboard access might be denied in some browsers
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasLegalConsent || !cleanUrl) return;

    setIsLoading(true);
    setErrorMsg(null);

    try {
      const res = await startLiveMeeting(
        workspaceId,
        cleanUrl,
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
      setErrorMsg(
        err.message || 'Failed to dispatch AI meeting capture bot. Please verify your link and try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xl animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isLoading) onClose();
      }}
    >
      {/* Background Decorative Glow */}
      <div className="absolute w-[500px] h-[500px] rounded-full bg-gradient-to-tr from-indigo-600/15 via-purple-600/10 to-emerald-500/10 blur-3xl pointer-events-none -z-10" />

      {/* Modal Container */}
      <div className="relative w-full max-w-3xl overflow-hidden rounded-3xl bg-[#0d0f17]/95 border border-white/10 shadow-[0_25px_70px_rgba(0,0,0,0.8),0_0_50px_rgba(99,102,241,0.12)] text-slate-100 flex flex-col">
        {/* Sleek top glowing border line */}
        <div className="h-1 w-full bg-gradient-to-r from-emerald-400 via-indigo-500 to-purple-500" />

        {/* Modal Header */}
        <div className="relative p-6 pb-5 flex items-start justify-between border-b border-white/[0.08]">
          <div className="flex items-start gap-4">
            {/* Ambient Icon Container */}
            <div className="relative flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-emerald-500/20 border border-indigo-500/30 text-indigo-300 shadow-inner shrink-0 group">
              <div className="absolute inset-0 rounded-2xl bg-indigo-500/10 blur-sm group-hover:blur-md transition-all" />
              <Video className="relative w-6 h-6 text-indigo-300" />
              <span className="absolute -bottom-1 -right-1 flex h-3.5 w-3.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-emerald-500 border-2 border-[#0d0f17]"></span>
              </span>
            </div>

            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h2 className="text-xl font-bold tracking-tight text-white">
                  Join Live Google Meet
                </h2>
                {/* <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 rounded-full shadow-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Self-Hosted Vexa Bot
                </span> */}
              </div>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Dispatch an autonomous AI companion into your meeting for live transcription & notes.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-white/[0.06] transition-all disabled:opacity-50"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Error Banner */}
          {errorMsg && (
            <div className="p-3.5 text-xs text-rose-200 bg-rose-950/50 border border-rose-500/40 rounded-2xl flex items-start gap-3 shadow-lg shadow-rose-950/30 animate-shake">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold text-rose-300">Connection Failed</p>
                <p className="text-rose-200/80 mt-0.5">{errorMsg}</p>
              </div>
            </div>
          )}

          {/* Google Meet URL Field */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <span>Google Meet Link or Code</span>
                <span className="text-rose-400">*</span>
              </label>

              {/* Paste helper */}
              <button
                type="button"
                onClick={handlePasteClipboard}
                className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1 transition-colors"
              >
                {hasCopiedUrl ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-400" />
                    <span className="text-emerald-400">Pasted!</span>
                  </>
                ) : (
                  <>
                    <Clipboard className="w-3 h-3" />
                    <span>Paste Link</span>
                  </>
                )}
              </button>
            </div>

            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400 group-focus-within:text-indigo-400 transition-colors">
                <Video className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={meetingUrl}
                onChange={(e) => setMeetingUrl(e.target.value)}
                placeholder="Meet URL"
                required
                className={`w-full pl-10 pr-24 py-3 text-sm text-white bg-black/40 border rounded-2xl placeholder-slate-500 focus:outline-none transition-all font-mono ${meetingUrl.trim().length > 0 && isMeetCodeOrUrl
                    ? 'border-emerald-500/50 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400'
                    : 'border-white/10 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20'
                  }`}
              />

              {/* Status pill inside right */}
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                {meetingUrl.trim().length > 0 ? (
                  isMeetCodeOrUrl ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded-lg border border-emerald-500/30">
                      <CheckCircle2 className="w-3 h-3" /> Valid Link
                    </span>
                  ) : (
                    <span className="text-[11px] text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded-lg border border-amber-500/30">
                      Check Code
                    </span>
                  )
                ) : (
                  <span className="text-[11px] text-slate-500 font-sans">Google Meet</span>
                )}
              </div>
            </div>
            <p className="text-[11px] text-slate-400 flex items-center gap-1">
              Supports full URL (<span className="text-slate-300 font-mono">meet.google.com/xxx-xxxx-xxx</span>) or 10-char room code.
            </p>
          </div>

          {/* Meeting Title Field (Optional) */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <span>Session Title</span>
                <span className="text-slate-500 text-[11px] font-normal normal-case">(Optional)</span>
              </label>
            </div>

            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400 group-focus-within:text-indigo-400 transition-colors">
                <FileText className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={meetingTitle}
                onChange={(e) => setMeetingTitle(e.target.value)}
                placeholder="e.g., Weekly Engineering Sync & Sprint Planning"
                className="w-full pl-10 pr-3.5 py-3 text-sm text-white bg-black/40 border border-white/10 rounded-2xl placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all"
              />
            </div>

            {/* Quick Title Suggestions */}
            <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
              <span className="text-[11px] text-slate-500 mr-1">Suggestions:</span>
              {quickTitles.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setMeetingTitle(t)}
                  className={`text-[11px] px-2.5 py-1 rounded-lg border transition-all ${meetingTitle === t
                      ? 'bg-indigo-600/30 text-indigo-300 border-indigo-500/50 font-medium'
                      : 'bg-white/[0.03] text-slate-400 border-white/[0.06] hover:text-slate-200 hover:bg-white/[0.06]'
                    }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* REDESIGNED: Legal Consent & Recording Compliance Card */}
          <div className="relative rounded-2xl bg-gradient-to-b from-amber-500/[0.07] to-indigo-500/[0.04] border border-amber-500/25 p-4 space-y-3.5 overflow-hidden">
            {/* Subtle background shield watermark */}
            <ShieldCheck className="absolute -right-4 -bottom-4 w-32 h-32 text-amber-500/[0.04] pointer-events-none" />

            {/* Card Header */}
            <div className="flex items-start gap-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-400 shrink-0">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-amber-300">
                    Mandatory Legal Consent Disclosure
                  </h4>
                  <span className="px-1.5 py-0.5 text-[9px] font-bold text-amber-400 bg-amber-500/20 rounded border border-amber-500/30 uppercase">
                    Required
                  </span>
                </div>
                <p className="text-xs text-amber-200/80 leading-relaxed">
                  You are dispatching an autonomous AI bot into an active call. Recording or transcribing meetings with the consent of all attendees is strictly prohibited by law in many jurisdictions.
                </p>
              </div>
            </div>

            {/* Interactive Consent Checkbox / Acceptance Box */}
            <label
              className={`flex items-start gap-3.5 p-3 rounded-xl border transition-all cursor-pointer select-none group ${hasLegalConsent
                  ? 'bg-gradient-to-r from-emerald-950/40 via-indigo-950/30 to-emerald-950/40 border-emerald-500/40 shadow-sm shadow-emerald-950/50'
                  : 'bg-black/50 border-amber-500/30 hover:border-amber-400/50 hover:bg-black/70'
                }`}
            >
              <div className="relative flex items-center justify-center shrink-0 mt-0.5">
                <input
                  type="checkbox"
                  checked={hasLegalConsent}
                  onChange={(e) => setHasLegalConsent(e.target.checked)}
                  className="sr-only"
                />
                <div
                  className={`w-5 h-5 rounded-lg flex items-center justify-center transition-all ${hasLegalConsent
                      ? 'bg-emerald-500 text-black shadow-md shadow-emerald-500/40 font-bold'
                      : 'border-2 border-slate-600 group-hover:border-amber-400 bg-black/60'
                    }`}
                >
                  {hasLegalConsent && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                </div>
              </div>

              <div className="space-y-0.5">
                <span
                  className={`text-xs font-semibold leading-snug transition-colors ${hasLegalConsent ? 'text-emerald-300' : 'text-slate-200 group-hover:text-white'
                    }`}
                >
                  I confirm all meeting participants have been informed and explicitly consented to AI recording & transcription.
                </span>
                <p className="text-[11px] text-slate-400 leading-tight">
                  Bot identity will be announced upon joining the Google Meet room.
                </p>
              </div>
            </label>
          </div>

          {/* Bot Capability Badges Tray */}
          <div className="grid grid-cols-2 gap-2.5 pt-1">
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs text-slate-300">
              <Radio className="w-3.5 h-3.5 text-cyan-400 shrink-0 animate-pulse" />
              <span className="truncate">Real-time WebSocket stream</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs text-slate-300">
              <Lock className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span className="truncate">Workspace-isolated privacy</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-2 border-t border-white/[0.08]">
            <div className="text-[11px] text-slate-500">
              {!hasLegalConsent && meetingUrl.trim().length > 0 && (
                <span className="text-amber-400/90 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> Check consent box to proceed
                </span>
              )}
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isLoading}
                className="px-4 py-2.5 text-xs font-medium text-slate-400 hover:text-white hover:bg-white/[0.06] rounded-xl transition-colors disabled:opacity-50"
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={!isFormValid}
                className={`relative group flex items-center gap-2 px-5 py-2.5 text-xs font-semibold rounded-xl transition-all shadow-xl overflow-hidden ${isFormValid
                    ? 'bg-gradient-to-r from-emerald-500 via-teal-500 to-indigo-600 text-white shadow-emerald-500/25 hover:shadow-emerald-500/40 hover:brightness-110 active:scale-[0.98] cursor-pointer'
                    : 'bg-slate-800/80 text-slate-500 border border-white/[0.06] cursor-not-allowed shadow-none'
                  }`}
              >
                {/* Glow effect on hover */}
                {isFormValid && (
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000" />
                )}

                {isLoading ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Dispatching Bot...</span>
                  </>
                ) : (
                  <>
                    <Bot className="w-4 h-4 text-white" />
                    <span>Dispatch Bot & Join Call</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
