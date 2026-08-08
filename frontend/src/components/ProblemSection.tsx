import React from 'react';
import { Mic, Bot, CheckSquare, Rocket } from 'lucide-react';

export const ProblemSection: React.FC = () => {
  const steps = [
    {
      emoji: '🎙️',
      title: 'Record',
      subtitle: 'Upload your meeting.',
      description: 'Sync live from Zoom, Google Meet, Teams, or drag & drop raw MP3/MP4 audio recordings.',
      icon: Mic,
      glow: 'hover:border-[#8B5CF6]/50 hover:shadow-[#8B5CF6]/10'
    },
    {
      emoji: '🤖',
      title: 'Understand',
      subtitle: 'AI listens.',
      description: 'Whisper HD diarization accurately recognizes speakers, cancels noise, and identifies key moments.',
      icon: Bot,
      glow: 'hover:border-[#3B82F6]/50 hover:shadow-[#3B82F6]/10'
    },
    {
      emoji: '✅',
      title: 'Organize',
      subtitle: 'Tasks appear automatically.',
      description: 'Extracts explicit commitments, assigns responsible owners, and tags realistic deadlines.',
      icon: CheckSquare,
      glow: 'hover:border-emerald-500/50 hover:shadow-emerald-500/10'
    },
    {
      emoji: '🚀',
      title: 'Execute',
      subtitle: 'Everyone knows what to do.',
      description: 'Automated sync pushes tickets straight to Linear, Jira, Notion, and Slack channels.',
      icon: Rocket,
      glow: 'hover:border-purple-500/50 hover:shadow-purple-500/10'
    }
  ];

  return (
    <section id="solution" className="py-20 lg:py-28 relative overflow-hidden bg-[#09090B] border-t border-[#27272A]">
      {/* Background glow orb */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-[#8B5CF6]/10 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Big Statement Header */}
        <div className="text-center max-w-4xl mx-auto space-y-4 mb-16">
          <h2 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold text-[#FAFAFA] tracking-tight leading-tight">
            Meetings shouldn't disappear after they end.
          </h2>

          <p className="text-slate-400 text-base sm:text-xl max-w-2xl mx-auto">
            Turn transient verbal chatter into permanent team memory and structured execution in four simple steps.
          </p>
        </div>

        {/* 4 Steps Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((st, idx) => {
            const Icon = st.icon;
            return (
              <div
                key={idx}
                className={`group p-6 sm:p-7 rounded-2xl bg-[#111113] border border-[#27272A] ${st.glow} transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl relative flex flex-col justify-between`}
              >
                <div>
                  <div className="flex items-center justify-between mb-6">
                    <span className="text-3xl p-2 rounded-xl bg-[#18181b] border border-[#27272A] group-hover:scale-110 transition-transform">
                      {st.emoji}
                    </span>
                    <span className="text-xs font-mono font-bold text-slate-500">
                      0{idx + 1}
                    </span>
                  </div>

                  <h3 className="text-xl font-bold text-[#FAFAFA] mb-1 group-hover:text-[#8B5CF6] transition-colors">
                    {st.title}
                  </h3>

                  <p className="text-sm font-semibold text-[#8B5CF6] mb-3">
                    {st.subtitle}
                  </p>

                  <p className="text-xs text-slate-400 leading-relaxed font-sans">
                    {st.description}
                  </p>
                </div>

                <div className="pt-5 mt-5 border-t border-[#27272A] flex items-center justify-between text-[11px] font-mono text-slate-500">
                  <span>Automated Workflow</span>
                  <Icon className="w-4 h-4 text-[#8B5CF6] group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </section>
  );
};

