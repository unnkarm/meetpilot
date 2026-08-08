import React, { useState } from 'react';
import { X, Play, Pause, Volume2, Sparkles, CheckCircle2 } from 'lucide-react';

interface WatchDemoModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const WatchDemoModal: React.FC<WatchDemoModalProps> = ({ isOpen, onClose }) => {
  const [isPlaying, setIsPlaying] = useState(true);
  const [activeTab, setActiveTab] = useState<'transcription' | 'tasks' | 'chat'>('transcription');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-3xl rounded-2xl bg-[#0b0d17] border border-white/20 p-6 shadow-2xl text-slate-200">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors z-10"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold">
            <Play className="w-4 h-4 fill-white ml-0.5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">MeetPilot AI Walkthrough</h3>
            <p className="text-xs text-slate-400">Interactive 90-second product demonstration</p>
          </div>
        </div>

        {/* Simulated Video Player Screen */}
        <div className="relative rounded-xl bg-[#05060a] border border-white/10 overflow-hidden shadow-inner aspect-video flex flex-col justify-between p-6">
          
          {/* Top Bar */}
          <div className="flex items-center justify-between text-xs">
            <span className="px-2.5 py-1 rounded bg-indigo-500/20 text-indigo-300 font-mono flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>AI Processing Live</span>
            </span>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('transcription')}
                className={`px-2.5 py-1 rounded text-xs transition-colors ${activeTab === 'transcription' ? 'bg-indigo-600 text-white font-semibold' : 'text-slate-400'}`}
              >
                1. Transcription
              </button>
              <button
                onClick={() => setActiveTab('tasks')}
                className={`px-2.5 py-1 rounded text-xs transition-colors ${activeTab === 'tasks' ? 'bg-indigo-600 text-white font-semibold' : 'text-slate-400'}`}
              >
                2. Task Extraction
              </button>
              <button
                onClick={() => setActiveTab('chat')}
                className={`px-2.5 py-1 rounded text-xs transition-colors ${activeTab === 'chat' ? 'bg-indigo-600 text-white font-semibold' : 'text-slate-400'}`}
              >
                3. Conversational RAG
              </button>
            </div>
          </div>

          {/* Center Stage Video Visual */}
          <div className="my-auto max-w-lg mx-auto text-center space-y-3">
            {activeTab === 'transcription' && (
              <div className="p-4 rounded-xl bg-white/[0.03] border border-indigo-500/30 space-y-2 animate-fadeIn">
                <div className="text-xs text-indigo-400 font-mono">00:18:24 - Speaker 01 (Sarah Chen)</div>
                <p className="text-sm font-medium text-white">
                  "We decided to deprecate custom JWTs and use OAuth 2.1 PKCE standards for security hardening."
                </p>
                <div className="text-[11px] text-emerald-400 font-semibold flex items-center justify-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> 99.8% Speaker Confidence
                </div>
              </div>
            )}

            {activeTab === 'tasks' && (
              <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 text-left space-y-2 animate-fadeIn">
                <div className="text-xs font-bold text-emerald-300">✔ Task Extracted Automatically</div>
                <div className="text-sm font-bold text-white">Complete OAuth 2.1 implementation spec</div>
                <div className="text-xs text-slate-300">Assignee: Sarah Chen • Due: Friday 5 PM</div>
              </div>
            )}

            {activeTab === 'chat' && (
              <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/30 text-left space-y-2 animate-fadeIn">
                <div className="text-xs text-slate-400">User Prompt: "Who owns deployment?"</div>
                <div className="text-sm text-indigo-200 font-medium">
                  "Marcus Vance is responsible for blue-green production deployment. Mentioned at 39:00."
                </div>
              </div>
            )}
          </div>

          {/* Bottom Player Controls */}
          <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-white/10">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center"
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-white ml-0.5" />}
              </button>
              <span className="font-mono">01:12 / 01:30</span>
            </div>

            <div className="flex items-center gap-2">
              <Volume2 className="w-4 h-4 text-indigo-400" />
              <span>1080p HD</span>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
};
