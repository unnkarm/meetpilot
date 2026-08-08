import React from 'react';
import { FileText, Users, CheckSquare, Search, Brain, Sparkles, ArrowUpRight } from 'lucide-react';

export const FeatureGrid: React.FC = () => {
  return (
    <section id="features" className="py-20 lg:py-28 relative overflow-hidden bg-[#09090B] border-t border-[#27272A]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 space-y-12">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#111113] border border-[#27272A] text-[#8B5CF6] text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-[#8B5CF6]" />
            <span>Productivity Architecture</span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-extrabold text-[#FAFAFA] tracking-tight">
            Built for execution.
          </h2>

          <p className="text-slate-400 text-base sm:text-lg">
            An intelligent meeting layer designed with the clarity of Linear and the speed of Raycast.
          </p>
        </div>

        {/* Bento Grid Layout */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* LARGE CARD 1: AI Summaries (Col Span 2) */}
          <div className="md:col-span-2 group p-8 rounded-2xl bg-[#111113] border border-[#27272A] hover:border-[#8B5CF6]/50 transition-all duration-300 relative overflow-hidden flex flex-col justify-between shadow-2xl">
            <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-br from-[#8B5CF6]/15 via-indigo-500/10 to-transparent blur-3xl pointer-events-none group-hover:opacity-100 opacity-60 transition-opacity" />

            <div>
              <div className="flex items-center justify-between mb-6">
                <div className="w-12 h-12 rounded-2xl bg-[#18181b] border border-[#27272A] flex items-center justify-center text-[#8B5CF6] group-hover:scale-110 transition-transform">
                  <FileText className="w-6 h-6" />
                </div>
                <span className="px-3 py-1 rounded-full bg-[#8B5CF6]/10 text-[#8B5CF6] border border-[#8B5CF6]/20 text-xs font-mono font-bold">
                  Core Engine
                </span>
              </div>

              <h3 className="text-2xl sm:text-3xl font-extrabold text-[#FAFAFA] mb-3 group-hover:text-[#8B5CF6] transition-colors">
                AI Summaries
              </h3>

              <p className="text-slate-300 text-base leading-relaxed max-w-xl font-normal">
                Reduce 60-minute meetings to 2 minutes. Instant executive digests filtering out filler chatter while capturing decisions, trade-offs, and consensus.
              </p>
            </div>

            <div className="pt-8 mt-8 border-t border-[#27272A] flex items-center justify-between text-xs font-mono text-slate-500">
              <span className="text-emerald-400">⚡ 95% time saved reading notes</span>
              <ArrowUpRight className="w-4 h-4 text-[#8B5CF6] group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </div>
          </div>

          {/* SMALL CARD 1: Speaker Recognition */}
          <div className="col-span-1 group p-6 rounded-2xl bg-[#111113] border border-[#27272A] hover:border-[#3B82F6]/50 transition-all duration-300 relative overflow-hidden flex flex-col justify-between shadow-2xl">
            <div>
              <div className="w-10 h-10 rounded-xl bg-[#18181b] border border-[#27272A] flex items-center justify-center text-[#3B82F6] mb-4 group-hover:scale-110 transition-transform">
                <Users className="w-5 h-5" />
              </div>

              <h3 className="text-xl font-bold text-[#FAFAFA] mb-2 group-hover:text-[#3B82F6] transition-colors">
                Speaker Recognition
              </h3>

              <p className="text-xs text-slate-400 leading-relaxed font-sans">
                Whisper HD diarization accurately assigns every spoken sentence to the exact team member with 0.1s timestamp precision.
              </p>
            </div>

            <div className="pt-4 mt-4 border-t border-[#27272A] text-[11px] font-mono text-slate-500">
              99.2% Diarization Accuracy
            </div>
          </div>

          {/* SMALL CARD 2: Action Items */}
          <div className="col-span-1 group p-6 rounded-2xl bg-[#111113] border border-[#27272A] hover:border-emerald-500/50 transition-all duration-300 relative overflow-hidden flex flex-col justify-between shadow-2xl">
            <div>
              <div className="w-10 h-10 rounded-xl bg-[#18181b] border border-[#27272A] flex items-center justify-center text-emerald-400 mb-4 group-hover:scale-110 transition-transform">
                <CheckSquare className="w-5 h-5" />
              </div>

              <h3 className="text-xl font-bold text-[#FAFAFA] mb-2 group-hover:text-emerald-400 transition-colors">
                Action Items
              </h3>

              <p className="text-xs text-slate-400 leading-relaxed font-sans">
                Auto-extracts explicit commitments, assigns responsible owners, sets realistic deadlines, and pushes tickets to Linear & Jira.
              </p>
            </div>

            <div className="pt-4 mt-4 border-t border-[#27272A] text-[11px] font-mono text-slate-500">
              Auto-Synced to Linear
            </div>
          </div>

          {/* SMALL CARD 3: AI Search */}
          <div className="col-span-1 group p-6 rounded-2xl bg-[#111113] border border-[#27272A] hover:border-purple-500/50 transition-all duration-300 relative overflow-hidden flex flex-col justify-between shadow-2xl">
            <div>
              <div className="w-10 h-10 rounded-xl bg-[#18181b] border border-[#27272A] flex items-center justify-center text-purple-400 mb-4 group-hover:scale-110 transition-transform">
                <Search className="w-5 h-5" />
              </div>

              <h3 className="text-xl font-bold text-[#FAFAFA] mb-2 group-hover:text-purple-400 transition-colors">
                AI Search
              </h3>

              <p className="text-xs text-slate-400 leading-relaxed font-sans">
                Natural language query across all past recordings. Ask "When did we decide to drop MySQL?" and jump to the exact moment.
              </p>
            </div>

            <div className="pt-4 mt-4 border-t border-[#27272A] text-[11px] font-mono text-slate-500">
              Instant Vector RAG
            </div>
          </div>

          {/* LARGE CARD 2: Meeting Memory */}
          <div className="col-span-1 group p-6 rounded-2xl bg-[#111113] border border-[#27272A] hover:border-[#8B5CF6]/50 transition-all duration-300 relative overflow-hidden flex flex-col justify-between shadow-2xl">
            <div>
              <div className="w-10 h-10 rounded-xl bg-[#18181b] border border-[#27272A] flex items-center justify-center text-[#8B5CF6] mb-4 group-hover:scale-110 transition-transform">
                <Brain className="w-5 h-5" />
              </div>

              <h3 className="text-xl font-bold text-[#FAFAFA] mb-2 group-hover:text-[#8B5CF6] transition-colors">
                Meeting Memory
              </h3>

              <p className="text-xs text-slate-400 leading-relaxed font-sans">
                Never forget what your team discussed. Permanent searchable knowledge base connecting discussions across months.
              </p>
            </div>

            <div className="pt-4 mt-4 border-t border-[#27272A] text-[11px] font-mono text-slate-500">
              100% Encrypted Store
            </div>
          </div>

        </div>

      </div>
    </section>
  );
};

