import React from 'react';
import { X, ShieldCheck, Lock, EyeOff, Server } from 'lucide-react';

interface PrivacyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PrivacyModal: React.FC<PrivacyModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-xl rounded-2xl bg-[#0e101c] border border-white/20 p-6 sm:p-8 shadow-2xl text-slate-200 space-y-6">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-xl font-extrabold text-white">Beta Data Handling</h3>
            <p className="text-xs text-slate-400">Workspace access and AI processing</p>
          </div>
        </div>

        {/* Principles */}
        <div className="space-y-4 text-xs text-slate-300">
          <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10 flex items-start gap-3">
            <EyeOff className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-white text-sm mb-1">AI Processing</h4>
              <p className="leading-relaxed text-slate-400">
                MeetPilot processes meeting data on the server running the service. When cloud AI is enabled, transcript context is sent to the configured AI provider. Using the web dashboard does not mean processing stays on your device.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10 flex items-start gap-3">
            <Lock className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-white text-sm mb-1">Stored Recordings</h4>
              <p className="leading-relaxed text-slate-400">
                MeetPilot stores recordings on the server running the service and checks workspace access before playback. This beta does not yet provide configurable retention or application-level file encryption.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10 flex items-start gap-3">
            <Server className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-white text-sm mb-1">Workspace Access</h4>
              <p className="leading-relaxed text-slate-400">
                Clerk verifies sign-in and the API checks workspace membership before serving meetings, documents and audio. This beta has no compliance certification.
              </p>
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
          <span>Current beta behavior</span>
          <button onClick={onClose} className="px-4 py-2 rounded-xl bg-indigo-600 text-white font-semibold hover:bg-indigo-500 transition-colors">
            I Understand
          </button>
        </div>

      </div>
    </div>
  );
};
