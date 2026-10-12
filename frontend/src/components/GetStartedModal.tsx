import { useEffect, useRef } from 'react';
import { X, Upload, ArrowRight, Sparkles } from 'lucide-react';
import { MeetPilotLogo } from './Logo';

interface GetStartedModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLaunchWorkspace: () => void;
}

export const GetStartedModal = ({ isOpen, onClose, onLaunchWorkspace }: GetStartedModalProps) => {
  const primaryButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    primaryButton.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const enterWorkspace = () => {
    onClose();
    onLaunchWorkspace();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div role="dialog" aria-modal="true" aria-labelledby="get-started-title" className="relative w-full max-w-lg rounded-2xl bg-[#0e101c] border border-white/20 p-6 sm:p-8 shadow-2xl text-slate-200">
        <button onClick={onClose} aria-label="Close" className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors">
          <X className="w-5 h-5" />
        </button>

        <div className="text-center space-y-2 mb-7">
          <MeetPilotLogo className="h-14 justify-center mb-3" iconOnly={true} />
          <h3 id="get-started-title" className="text-2xl font-extrabold text-white">Start with a real meeting</h3>
          <p className="text-sm text-slate-400">
            Sign in, create a workspace, then upload a recording. You can also open a separate sample workspace to explore the results first.
          </p>
        </div>

        <div className="space-y-3">
          <div className="p-4 rounded-xl border border-[#27272A] bg-[#111113] flex items-start gap-3">
            <Upload className="w-5 h-5 text-[#8B5CF6] shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-white text-sm">Upload in your workspace</div>
              <p className="text-xs text-slate-400 mt-1">Supported audio: MP3, MP4, M4A, AAC, WAV, WebM, OGG and FLAC. The configured limit is 250 MB.</p>
            </div>
          </div>
          <div className="p-4 rounded-xl border border-[#27272A] bg-[#111113] flex items-start gap-3">
            <Sparkles className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-white text-sm">Explore sample results</div>
              <p className="text-xs text-slate-400 mt-1">Choose Explore Demo inside the app for clearly marked sample meetings, tasks, decisions and a document.</p>
            </div>
          </div>
          <button ref={primaryButton} onClick={enterWorkspace} className="w-full py-3.5 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white font-bold text-sm shadow-lg shadow-indigo-500/30 flex items-center justify-center gap-2 transition-all">
            Continue to Workspace <ArrowRight className="w-4 h-4" />
          </button>
          <p className="text-[11px] text-center text-slate-500">Clerk sign-in is required to access workspace data.</p>
        </div>
      </div>
    </div>
  );
};
