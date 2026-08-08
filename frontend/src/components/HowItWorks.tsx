import React, { useState } from 'react';
import { Video, Mic, FileText, CheckSquare, LayoutDashboard, CheckCircle2, Sparkles, ArrowRight } from 'lucide-react';

export const HowItWorks: React.FC = () => {
  const [activeStep, setActiveStep] = useState<number>(2);

  const pipelineNodes = [
    {
      title: 'Meeting',
      desc: 'Live audio or MP4/Zoom sync',
      icon: Video,
      badge: 'Input'
    },
    {
      title: 'Transcript',
      desc: 'Whisper HD speaker diarization',
      icon: Mic,
      badge: '0.4s'
    },
    {
      title: 'Summary',
      desc: 'Concise executive takeaways',
      icon: FileText,
      badge: 'AI Digest'
    },
    {
      title: 'Tasks',
      desc: 'Auto-assigned to Linear & Jira',
      icon: CheckSquare,
      badge: 'Extracted'
    },
    {
      title: 'Workspace',
      desc: 'Searchable team memory store',
      icon: LayoutDashboard,
      badge: 'RAG Index'
    },
    {
      title: 'Completed',
      desc: 'Zero follow-up friction',
      icon: CheckCircle2,
      badge: 'Done'
    }
  ];

  return (
    <section id="how-it-works" className="py-20 lg:py-28 relative overflow-hidden bg-[#09090B] border-t border-[#27272A]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 space-y-14">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#111113] border border-[#27272A] text-[#8B5CF6] text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-[#8B5CF6]" />
            <span>End-To-End Execution Engine</span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-extrabold text-[#FAFAFA] tracking-tight">
            How MeetPilot AI Works
          </h2>

          <p className="text-slate-400 text-base sm:text-lg">
            Watch your raw audio transform across the six-stage intelligence pipeline.
          </p>
        </div>

        {/* Horizontal Pipeline Workflow */}
        <div className="relative">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 relative z-10">
            {pipelineNodes.map((node, idx) => {
              const Icon = node.icon;
              const isCurrent = activeStep === idx;
              const isPassed = activeStep >= idx;

              return (
                <div
                  key={idx}
                  onClick={() => setActiveStep(idx)}
                  className={`p-5 rounded-2xl cursor-pointer transition-all duration-300 border flex flex-col justify-between group ${
                    isCurrent
                      ? 'bg-[#18181b] border-[#8B5CF6] shadow-xl shadow-[#8B5CF6]/20 scale-105'
                      : isPassed
                      ? 'bg-[#111113] border-[#3B82F6]/40 text-[#FAFAFA]'
                      : 'bg-[#111113] border-[#27272A] text-slate-500 hover:border-[#8B5CF6]/40'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <span className={`text-[9px] font-mono px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                        isCurrent
                          ? 'bg-[#8B5CF6]/20 text-[#8B5CF6] border border-[#8B5CF6]/40'
                          : 'bg-[#18181b] text-slate-400 border border-[#27272A]'
                      }`}>
                        {node.badge}
                      </span>
                      <Icon className={`w-4 h-4 ${isCurrent ? 'text-[#8B5CF6]' : 'text-slate-500'}`} />
                    </div>

                    <h3 className={`font-syne text-xs font-bold uppercase tracking-tight ${isCurrent ? 'text-white' : 'text-slate-300'}`}>
                      {node.title}
                    </h3>

                    <p className="text-[10px] font-grotesk text-slate-400 mt-2 leading-tight">
                      {node.desc}
                    </p>
                  </div>

                  <div className="pt-3 mt-3 border-t border-[#27272A] text-[9px] font-mono text-slate-500 flex justify-between">
                    <span>STAGE 0{idx + 1}</span>
                    <span>{isCurrent ? 'ACTIVE' : 'READY'}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Stage Detail Showcase */}
        <div className="max-w-3xl mx-auto p-6 sm:p-8 rounded-2xl bg-[#111113] border border-[#8B5CF6]/30 shadow-2xl space-y-4 text-center">
          <div className="flex items-center justify-center gap-2 text-xs font-mono text-[#8B5CF6] uppercase tracking-wider">
            <span>Stage 0{activeStep + 1} Pipeline Detail</span>
          </div>

          <h3 className="text-2xl font-bold text-[#FAFAFA]">
            {pipelineNodes[activeStep].title}: {pipelineNodes[activeStep].desc}
          </h3>

          <p className="text-sm text-slate-300 leading-relaxed max-w-xl mx-auto">
            MeetPilot handles high-throughput audio ingestion, semantic embedding, automated action extraction, and cross-platform notification webhooks in real time.
          </p>

          <div className="pt-2 flex justify-center">
            <button
              onClick={() => setActiveStep((prev) => (prev + 1) % pipelineNodes.length)}
              className="px-5 py-2.5 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] text-white font-bold text-xs flex items-center gap-2 transition-colors cursor-pointer"
            >
              <span>Advance Pipeline Node</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

      </div>
    </section>
  );
};

