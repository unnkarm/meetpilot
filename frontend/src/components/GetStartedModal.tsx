import { X, Upload, Sparkles, CheckCircle2, ArrowRight, FileAudio } from 'lucide-react';
import { MeetPilotLogo } from './Logo';

interface GetStartedModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLaunchWorkspace: () => void;
}

export const GetStartedModal: React.FC<GetStartedModalProps> = ({
  isOpen,
  onClose,
  onLaunchWorkspace
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processStep, setProcessStep] = useState(0);

  if (!isOpen) return null;

  const handleSimulateUpload = (file?: File) => {
    const sampleFile = file || new File(["sample audio content"], "Weekly_Sprint_Planning.mp3", { type: "audio/mp3" });
    setUploadedFile(sampleFile);
    setIsProcessing(true);

    // Simulate 3 progress steps
    setProcessStep(1); // Transcribing
    setTimeout(() => setProcessStep(2), 1200); // Summarizing
    setTimeout(() => {
      setProcessStep(3); // Complete
      setTimeout(() => {
        setIsProcessing(false);
        onClose();
        onLaunchWorkspace();
      }, 800);
    }, 2400);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-lg rounded-2xl bg-[#0e101c] border border-white/20 p-6 sm:p-8 shadow-2xl text-slate-200">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="text-center space-y-2 mb-6">
          <MeetPilotLogo className="h-14 justify-center mb-3" iconOnly={true} />

          <h3 className="text-2xl font-extrabold text-white">
            Get Started with MeetPilot AI
          </h3>
          <p className="text-xs text-slate-400">
            Upload a meeting recording or jump straight into the interactive workspace.
          </p>
        </div>

        {/* Processing State */}
        {isProcessing ? (
          <div className="py-8 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-indigo-500/20 border-2 border-indigo-500 border-t-transparent animate-spin mx-auto flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-indigo-400 animate-pulse" />
            </div>

            <div className="space-y-1">
              <div className="text-base font-bold text-white">
                {processStep === 1 && "1/3 Transcribing audio with Whisper HD..."}
                {processStep === 2 && "2/3 Extracting action items & key decisions..."}
                {processStep === 3 && "3/3 Workspace ready! Opening dashboard..."}
              </div>
              <p className="text-xs text-slate-400">File: {uploadedFile?.name}</p>
            </div>
          </div>
        ) : (
          /* Normal Upload & Workspace Launch Options */
          <div className="space-y-4">
            
            {/* Drag and Drop Zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragActive(false);
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  handleSimulateUpload(e.dataTransfer.files[0]);
                }
              }}
              onClick={() => handleSimulateUpload()}
              className={`p-8 rounded-xl border-2 border-dashed transition-all cursor-pointer text-center flex flex-col items-center justify-center gap-3 ${
                dragActive
                  ? 'border-indigo-400 bg-indigo-500/20'
                  : 'border-white/15 bg-white/[0.02] hover:border-indigo-500/50 hover:bg-white/[0.05]'
              }`}
            >
              <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Upload className="w-6 h-6" />
              </div>

              <div>
                <div className="text-sm font-bold text-white">
                  Click or drag audio file to transcribe
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  Supports MP3, MP4, M4A, WAV (Max 500MB)
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 text-xs text-slate-500">
              <span className="h-px bg-white/10 flex-1"></span>
              <span>OR</span>
              <span className="h-px bg-white/10 flex-1"></span>
            </div>

            {/* Instant Demo Launch Button */}
            <button
              onClick={() => {
                onClose();
                onLaunchWorkspace();
              }}
              className="w-full py-3.5 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white font-bold text-sm shadow-lg shadow-indigo-500/30 flex items-center justify-center gap-2 transition-all"
            >
              <span>Explore Pre-Populated Workspace Demo</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <div className="text-[11px] text-center text-slate-400 pt-1">
              ✨ No sign up required for instant preview mode.
            </div>

          </div>
        )}

      </div>
    </div>
  );
};
