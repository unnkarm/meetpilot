import React from 'react';
import { X, Target, Compass, Cpu, ArrowRight, CheckCircle2 } from 'lucide-react';
import { MeetPilotLogo } from './Logo';
import { TECH_STACK } from '../data/landingData';

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenGetStarted: () => void;
}

export const AboutModal: React.FC<AboutModalProps> = ({ isOpen, onClose, onOpenGetStarted }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-4xl rounded-2xl bg-[#0e101c] border border-white/20 p-6 sm:p-8 shadow-2xl text-slate-200 max-h-[90vh] overflow-y-auto space-y-8">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="text-center space-y-3">
          <MeetPilotLogo className="h-14 justify-center" iconOnly={true} />

          <h3 className="text-3xl font-extrabold text-white">
            About MeetPilot AI
          </h3>

          <p className="text-slate-400 text-sm max-w-lg mx-auto leading-relaxed">
            Eliminating meeting clutter so engineering and product teams can focus strictly on high-velocity execution.
          </p>
        </div>

        {/* Story Section */}
        <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-3">
          <div className="text-xs font-mono text-[#8B5CF6] uppercase font-bold tracking-wider">The Origin Story</div>
          <blockquote className="text-lg sm:text-xl font-extrabold text-white leading-snug">
            "Meetings create work, but the work gets lost."
          </blockquote>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            Every day, engineering and product teams spend hundreds of hours discussing specs, architecture decisions, and task assignees in video calls. Yet 20 minutes later, commitments are forgotten, deadlines slip, and teams waste time re-asking "Who agreed to handle authentication?" MeetPilot AI was built as an invisible intelligence layer that turns live voice into structured workspace memory and automated ticket execution.
          </p>
        </div>

        {/* Mission & Vision Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-3">
            <div className="w-10 h-10 rounded-xl bg-[#8B5CF6]/10 text-[#8B5CF6] flex items-center justify-center">
              <Target className="w-5 h-5" />
            </div>
            <h4 className="text-lg font-bold text-white">Our Mission</h4>
            <p className="text-xs text-slate-300 leading-relaxed">
              To convert unformatted meeting speech into immediate, clear action items, eliminating follow-up friction for high-growth software teams worldwide.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-3">
            <div className="w-10 h-10 rounded-xl bg-[#3B82F6]/10 text-[#3B82F6] flex items-center justify-center">
              <Compass className="w-5 h-5" />
            </div>
            <h4 className="text-lg font-bold text-white">Our Vision</h4>
            <p className="text-xs text-slate-300 leading-relaxed">
              A world where no team member ever manually writes meeting notes, takes manual action item logs, or forgets a past design decision again.
            </p>
          </div>
        </div>

        {/* Tech Stack */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-[#8B5CF6]" />
            <h4 className="text-sm font-bold text-white uppercase tracking-wider">Engineered Infrastructure Stack</h4>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {TECH_STACK.map((tech, idx) => (
              <div key={idx} className="p-3.5 rounded-xl bg-[#111113] border border-[#27272A] space-y-1">
                <div className={`text-xs font-bold ${tech.color}`}>{tech.name}</div>
                <div className="text-[11px] text-slate-400 leading-tight">{tech.role}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Product Roadmap */}
        <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4">
          <h4 className="text-sm font-bold text-white uppercase tracking-wider">Product Roadmap</h4>
          
          <div className="space-y-3 text-xs">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-white">Q3 2026: Whisper HD Real-time WebRTC Streaming</span>
                <p className="text-slate-400">Live sub-second transcript streaming with auto speaker diarization.</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-[#8B5CF6] shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-white">Q4 2026: Deep Bidirectional Linear & Jira Sync</span>
                <p className="text-slate-400">Two-way ticket state updates directly from AI action item completions.</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-white">Q1 2027: Enterprise Air-Gapped On-Premises Vault</span>
                <p className="text-slate-400">Self-hosted LLM & pgvector indexing for financial and defense clients.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer CTA */}
        <div className="pt-4 border-t border-[#27272A] flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="text-xs text-slate-400">Join 1,200+ engineering teams already executing faster.</span>
          <button
            onClick={() => { onClose(); onOpenGetStarted(); }}
            className="px-6 py-2.5 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] text-white font-bold text-xs flex items-center gap-2 transition-colors cursor-pointer"
          >
            <span>Launch Workspace</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

      </div>
    </div>
  );
};
