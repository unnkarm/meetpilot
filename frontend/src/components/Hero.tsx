import React, { useState, useEffect } from 'react';
import { Sparkles, Play, ArrowRight, Check, MousePointer2 } from 'lucide-react';

interface HeroProps {
  onOpenGetStarted: () => void;
  onOpenWatchDemo: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onOpenGetStarted, onOpenWatchDemo }) => {
  const [typedQuote, setTypedQuote] = useState('');
  const fullQuote = '"Sarah owns Authentication architecture"';

  // Animated typing effect for the floating badge quote
  useEffect(() => {
    let index = 0;
    const interval = setInterval(() => {
      setTypedQuote(fullQuote.slice(0, index));
      index++;
      if (index > fullQuote.length) {
        setTimeout(() => {
          index = 0;
        }, 3000);
      }
    }, 120);

    return () => clearInterval(interval);
  }, []);

  return (
    <section className="relative overflow-hidden pt-12 pb-16 lg:pt-20 lg:pb-28 bg-[#09090B] bg-grid-pattern">
      {/* Background radial glowing orbs */}
      <div className="absolute top-1/4 left-1/3 -translate-x-1/2 w-[550px] h-[350px] bg-purple-600/15 blur-[140px] pointer-events-none rounded-full" />
      <div className="absolute top-1/3 right-10 w-[450px] h-[300px] bg-blue-600/15 blur-[140px] pointer-events-none rounded-full" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          
          {/* LEFT SIDE CONTENT */}
          <div className="lg:col-span-6 space-y-6 text-left">
            
            {/* Small Badge */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#111113] border border-[#27272A] text-[#8B5CF6] text-xs font-semibold tracking-wide shadow-sm hover:border-[#8B5CF6]/40 transition-colors">
              <Sparkles className="w-3.5 h-3.5 text-[#8B5CF6] animate-pulse" />
              <span>AI Meeting Intelligence Platform</span>
            </div>

            {/* Large Headline */}
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-[#FAFAFA] leading-[1.05]">
              Meet less.<br />
              <span className="bg-gradient-to-r from-[#8B5CF6] via-indigo-300 to-[#3B82F6] bg-clip-text text-transparent">
                Execute more.
              </span>
            </h1>

            {/* Subheadline */}
            <p className="text-lg sm:text-xl text-slate-300 leading-relaxed font-normal max-w-xl">
              MeetPilot transforms every meeting into searchable knowledge, AI summaries, and actionable tasks.
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 pt-2">
              <button
                onClick={onOpenGetStarted}
                className="px-7 py-3.5 rounded-xl text-base font-bold text-white bg-[#8B5CF6] hover:bg-[#7c3aed] shadow-lg shadow-[#8B5CF6]/30 hover:shadow-[#8B5CF6]/50 transition-all duration-200 flex items-center justify-center gap-2 group cursor-pointer"
              >
                <span>Get Started</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>

              <button
                onClick={onOpenWatchDemo}
                className="px-6 py-3.5 rounded-xl text-base font-semibold text-[#FAFAFA] bg-[#111113] hover:bg-[#18181b] border border-[#27272A] hover:border-[#8B5CF6]/40 transition-all duration-200 flex items-center justify-center gap-2.5 group cursor-pointer"
              >
                <div className="w-6 h-6 rounded-full bg-[#8B5CF6]/20 flex items-center justify-center group-hover:bg-[#8B5CF6]/30 transition-colors">
                  <Play className="w-3 h-3 text-[#8B5CF6] fill-[#8B5CF6] ml-0.5" />
                </div>
                <span>Watch Demo</span>
              </button>
            </div>

            {/* Underneath Trust Line */}
            <p className="text-xs text-slate-400 pt-1 font-mono flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>No credit card • Free forever • 2-minute setup</span>
            </p>

          </div>

          {/* RIGHT SIDE FLOATING ANIMATED DASHBOARD */}
          <div className="lg:col-span-6 relative">
            
            {/* Glowing background halo */}
            <div className="absolute -inset-1.5 rounded-3xl bg-gradient-to-r from-[#8B5CF6]/30 via-[#3B82F6]/20 to-indigo-500/30 blur-2xl opacity-70 animate-pulse-glow" />

            <div className="relative rounded-2xl bg-[#111113] border border-[#27272A] p-6 sm:p-8 shadow-2xl shadow-black/90 space-y-6 transition-all duration-500 hover:border-[#8B5CF6]/40">
              
              {/* Card Title */}
              <div className="flex items-center justify-between pb-4 border-b border-[#27272A]">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
                  <div className="w-3 h-3 rounded-full bg-amber-500/80"></div>
                  <div className="w-3 h-3 rounded-full bg-emerald-500/80"></div>
                  <span className="ml-2 text-sm font-bold text-[#FAFAFA]">Sprint Planning</span>
                </div>
                <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-mono">
                  Live Sync
                </span>
              </div>

              {/* Status List with Checkmarks */}
              <div className="space-y-3 font-mono text-sm text-slate-300">
                <div className="flex items-center gap-3 p-3 rounded-xl bg-[#18181b] border border-[#27272A] hover:border-[#8B5CF6]/30 transition-colors group">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-[#FAFAFA] font-medium">Transcript Ready</span>
                  <span className="ml-auto text-xs text-slate-500">0.4s</span>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-xl bg-[#18181b] border border-[#27272A] hover:border-[#8B5CF6]/30 transition-colors group">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-[#FAFAFA] font-medium">Summary Generated</span>
                  <span className="ml-auto text-xs text-slate-500">Key insights</span>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-xl bg-[#18181b] border border-[#27272A] hover:border-[#8B5CF6]/30 transition-colors group">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-[#FAFAFA] font-medium">12 Tasks Extracted</span>
                  <span className="ml-auto text-xs text-slate-500">Auto-assigned</span>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-xl bg-[#18181b] border border-[#27272A] hover:border-[#8B5CF6]/30 transition-colors group">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-[#FAFAFA] font-medium">4 Decisions Found</span>
                  <span className="ml-auto text-xs text-slate-500">Consensus</span>
                </div>
              </div>

              {/* Animated Quote Callout Card */}
              <div className="relative p-4 rounded-xl bg-gradient-to-r from-[#8B5CF6]/20 via-[#3B82F6]/15 to-[#18181b] border border-[#8B5CF6]/40 text-sm font-mono text-[#FAFAFA] flex items-center justify-between shadow-lg">
                <div className="flex items-center gap-2">
                  <span className="text-[#8B5CF6] font-bold">AI Insight:</span>
                  <span className="text-emerald-300 font-semibold">{typedQuote}</span>
                  <span className="w-2 h-4 bg-[#8B5CF6] animate-cursor"></span>
                </div>
                
                {/* Floating animated cursor icon */}
                <div className="absolute -bottom-3 -right-2 p-1.5 rounded-lg bg-[#8B5CF6] text-white shadow-lg animate-bounce">
                  <MousePointer2 className="w-3.5 h-3.5" />
                </div>
              </div>

            </div>
          </div>

        </div>
      </div>
    </section>
  );
};
