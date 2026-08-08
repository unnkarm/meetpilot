import React, { useState } from 'react';
import { Mic, FileText, CheckSquare, MessageSquare, Database, Sparkles, Check, ArrowUpRight } from 'lucide-react';

interface SolutionSectionProps {
  onOpenGetStarted: () => void;
}

export const SolutionSection: React.FC<SolutionSectionProps> = ({ onOpenGetStarted }) => {
  const [activeCard, setActiveCard] = useState<number>(0);

  const solutions = [
    {
      id: 0,
      icon: Mic,
      emoji: "🎙️",
      title: "AI Transcription",
      headline: "Every word becomes searchable.",
      description: "Whisper-level accuracy speaker diarization that indexes every phrase, technical acronym, and participant contribution instantly.",
      preview: {
        type: "transcript",
        speaker: "Sarah Chen",
        timestamp: "18:24",
        text: "I am taking ownership of the authentication refactor and will deliver the spec by Friday.",
        highlight: "authentication refactor"
      }
    },
    {
      id: 1,
      icon: FileText,
      emoji: "📝",
      title: "Smart Summaries",
      headline: "Understand an hour-long meeting in 30 seconds.",
      description: "Structured executive summaries that extract core themes, major decisions, and key takeaways without fluff or filler.",
      preview: {
        type: "summary",
        bullet1: "Auth service migrating to OAuth 2.1 PKCE to enhance token security.",
        bullet2: "Redis rate-limiting configured for sub-5ms transcript lookup speed.",
        bullet3: "Bi-weekly blue-green deployments approved for production releases."
      }
    },
    {
      id: 2,
      icon: CheckSquare,
      emoji: "✅",
      title: "Action Items",
      headline: "Automatically extract tasks, owners, and deadlines.",
      description: "Never lose momentum. MeetPilot AI identifies commitments made during discussions and parses who owns what and when it is due.",
      preview: {
        type: "task",
        title: "Complete OAuth 2.1 authentication flow",
        assignee: "Sarah Chen",
        due: "This Friday",
        status: "Auto-extracted"
      }
    },
    {
      id: 3,
      icon: MessageSquare,
      emoji: "💬",
      title: "AI Chat",
      headline: "Ask: 'Who owns deployment?' and receive answers instantly.",
      description: "Contextual RAG engine connected directly to your meeting audio. Ask any question in plain language and get citation timestamps.",
      preview: {
        type: "chat",
        question: "Who owns deployment?",
        answer: "Marcus Vance is responsible for blue-green production deployment.",
        timestamp: "39:00"
      }
    },
    {
      id: 4,
      icon: Database,
      emoji: "📂",
      title: "Meeting Memory",
      headline: "Every discussion becomes searchable forever.",
      description: "A centralized knowledge base of organizational memory so new team members can search past decisions and onboarding context.",
      preview: {
        type: "memory",
        query: "Architecture decisions from July",
        resultsCount: "14 matching decisions found across 6 meetings"
      }
    }
  ];

  return (
    <section id="solution" className="py-20 lg:py-28 relative overflow-hidden bg-[#09090B] border-t border-[#27272A]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 space-y-14">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#111113] border border-[#27272A] text-[#8B5CF6] text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-[#8B5CF6]" />
            <span>The MeetPilot AI Solution</span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-extrabold text-[#FAFAFA] tracking-tight">
            MeetPilot AI fixes that.
          </h2>

          <p className="text-slate-400 text-base sm:text-lg">
            Turn passive talk into active execution. Five intelligent engines working seamlessly to turn meeting audio into structured team intelligence.
          </p>
        </div>

        {/* Interactive Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
          
          {/* Solution Selector Cards (Left 7 cols) */}
          <div className="lg:col-span-7 space-y-3">
            {solutions.map((sol, index) => {
              const isSelected = activeCard === index;
              return (
                <div
                  key={sol.id}
                  onClick={() => setActiveCard(index)}
                  className={`p-5 rounded-2xl cursor-pointer transition-all duration-300 border ${
                    isSelected
                      ? 'bg-[#18181b] border-[#8B5CF6] shadow-xl shadow-[#8B5CF6]/10'
                      : 'bg-[#111113] border-[#27272A] hover:border-[#8B5CF6]/40 hover:bg-[#18181b]'
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div className={`w-11 h-11 rounded-xl flex items-center justify-center text-xl shrink-0 transition-transform ${
                      isSelected ? 'bg-[#8B5CF6]/20 border border-[#8B5CF6] scale-105' : 'bg-[#18181b] border border-[#27272A]'
                    }`}>
                      <span>{sol.emoji}</span>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <h3 className={`text-base font-bold transition-colors ${isSelected ? 'text-[#8B5CF6]' : 'text-white'}`}>
                          {sol.title}
                        </h3>
                        {isSelected && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-[#8B5CF6]/20 text-[#8B5CF6] border border-[#8B5CF6]/30 font-mono">
                            ACTIVE
                          </span>
                        )}
                      </div>
                      <p className="text-sm font-semibold text-slate-200 mt-0.5">
                        {sol.headline}
                      </p>
                      <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
                        {sol.description}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Live Preview Display (Right 5 cols) */}
          <div className="lg:col-span-5 flex flex-col">
            <div className="relative flex-1 rounded-2xl bg-[#111113] border border-[#27272A] p-6 shadow-2xl flex flex-col justify-between overflow-hidden">
              <div className="absolute top-0 right-0 w-48 h-48 bg-[#8B5CF6]/10 blur-[80px] pointer-events-none" />

              <div>
                <div className="flex items-center justify-between pb-4 border-b border-[#27272A]">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#8B5CF6] animate-pulse"></span>
                    <span className="text-xs font-bold uppercase tracking-wider text-[#8B5CF6]">
                      Live Output Simulator
                    </span>
                  </div>
                  <span className="text-xs font-mono text-slate-400">
                    {solutions[activeCard].title}
                  </span>
                </div>

                {/* Preview Content based on selected card */}
                <div className="py-6">
                  {solutions[activeCard].preview.type === 'transcript' && (
                    <div className="space-y-4">
                      <div className="p-4 rounded-xl bg-[#18181b] border border-[#27272A] space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-white">{solutions[activeCard].preview.speaker}</span>
                          <span className="text-[#8B5CF6] font-mono">@{solutions[activeCard].preview.timestamp}</span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          "I am taking ownership of the <mark className="bg-[#8B5CF6]/30 text-[#8B5CF6] font-semibold px-1 rounded">authentication refactor</mark> and will deliver the spec by Friday."
                        </p>
                      </div>
                      <div className="text-[11px] text-slate-500 text-center font-mono">
                        🔍 Search terms highlighted in sub-10ms
                      </div>
                    </div>
                  )}

                  {solutions[activeCard].preview.type === 'summary' && (
                    <div className="space-y-3">
                      <div className="p-3.5 rounded-xl bg-[#18181b] border border-[#27272A] text-xs text-slate-300 flex items-start gap-2">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{solutions[activeCard].preview.bullet1}</span>
                      </div>
                      <div className="p-3.5 rounded-xl bg-[#18181b] border border-[#27272A] text-xs text-slate-300 flex items-start gap-2">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{solutions[activeCard].preview.bullet2}</span>
                      </div>
                      <div className="p-3.5 rounded-xl bg-[#18181b] border border-[#27272A] text-xs text-slate-300 flex items-start gap-2">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{solutions[activeCard].preview.bullet3}</span>
                      </div>
                    </div>
                  )}

                  {solutions[activeCard].preview.type === 'task' && (
                    <div className="p-4 rounded-xl bg-[#18181b] border border-emerald-500/30 space-y-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold text-[10px]">
                          {solutions[activeCard].preview.status}
                        </span>
                        <span className="text-slate-400 text-[11px]">Due: {solutions[activeCard].preview.due}</span>
                      </div>
                      <div className="text-sm font-bold text-white">
                        {solutions[activeCard].preview.title}
                      </div>
                      <div className="flex items-center gap-2 pt-2 border-t border-[#27272A] text-xs text-slate-300">
                        <span className="w-5 h-5 rounded-full bg-[#8B5CF6] text-white font-bold text-[10px] flex items-center justify-center">SC</span>
                        <span>Assignee: <strong>{solutions[activeCard].preview.assignee}</strong></span>
                      </div>
                    </div>
                  )}

                  {solutions[activeCard].preview.type === 'chat' && (
                    <div className="space-y-3">
                      <div className="p-3 rounded-xl bg-[#18181b] border border-[#27272A] text-xs text-slate-200 font-medium">
                        🙋‍♂️ You: "{solutions[activeCard].preview.question}"
                      </div>
                      <div className="p-3.5 rounded-xl bg-[#8B5CF6]/10 border border-[#8B5CF6]/30 text-xs text-[#FAFAFA] space-y-1">
                        <div className="font-bold flex items-center gap-1.5 text-[#8B5CF6]">
                          <Sparkles className="w-3.5 h-3.5 text-[#8B5CF6]" /> MeetPilot AI
                        </div>
                        <p>{solutions[activeCard].preview.answer}</p>
                        <div className="text-[10px] text-[#8B5CF6] pt-1 font-mono">
                          Citation timestamp: @{solutions[activeCard].preview.timestamp}
                        </div>
                      </div>
                    </div>
                  )}

                  {solutions[activeCard].preview.type === 'memory' && (
                    <div className="p-4 rounded-xl bg-[#18181b] border border-[#27272A] space-y-3">
                      <div className="text-xs text-slate-400">Search Query:</div>
                      <div className="p-2.5 rounded-lg bg-[#09090B] text-xs font-mono text-[#8B5CF6] border border-[#27272A]">
                        "{solutions[activeCard].preview.query}"
                      </div>
                      <div className="text-xs text-emerald-400 font-semibold flex items-center gap-1.5">
                        <Check className="w-4 h-4" /> {solutions[activeCard].preview.resultsCount}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Bottom CTA within simulator */}
              <div className="pt-4 border-t border-[#27272A]">
                <button
                  onClick={onOpenGetStarted}
                  className="w-full py-2.5 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] text-white font-semibold text-xs flex items-center justify-center gap-2 transition-all cursor-pointer shadow-lg shadow-[#8B5CF6]/20"
                >
                  <span>Try {solutions[activeCard].title} Free</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>

            </div>
          </div>

        </div>

      </div>
    </section>
  );
};

