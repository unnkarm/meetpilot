import React from 'react';
import { Sparkles, ArrowRight, ShieldCheck, Check } from 'lucide-react';

interface CTASectionProps {
  onOpenGetStarted: () => void;
}

export const CTASection: React.FC<CTASectionProps> = ({ onOpenGetStarted }) => {
  return (
    <section className="py-20 lg:py-28 relative overflow-hidden bg-[#09090B] border-t border-[#27272A]">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] bg-gradient-to-r from-[#8B5CF6]/20 via-[#3B82F6]/10 to-indigo-600/20 blur-[100px] rounded-full pointer-events-none" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center space-y-6">
        
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#111113] border border-[#27272A] text-[#8B5CF6] text-xs font-semibold uppercase tracking-wider">
          <Sparkles className="w-3.5 h-3.5 text-[#8B5CF6]" />
          <span>Transform Your Team's Productivity</span>
        </div>

        <h2 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold text-[#FAFAFA] tracking-tight leading-tight">
          Ready to stop losing information?
        </h2>

        <p className="text-base sm:text-xl text-slate-300 max-w-2xl mx-auto leading-relaxed font-normal">
          Join high-growth engineering, product, and leadership teams turning unstructured meeting talk into instant clarity and automated execution.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <button
            onClick={onOpenGetStarted}
            className="w-full sm:w-auto px-9 py-4 rounded-xl text-base font-bold text-white bg-[#8B5CF6] hover:bg-[#7c3aed] shadow-2xl shadow-[#8B5CF6]/30 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2.5 group cursor-pointer"
          >
            <span>Start Free</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-6 pt-4 text-xs text-slate-400">
          <span className="flex items-center gap-1.5">
            <Check className="w-4 h-4 text-emerald-400" /> No credit card required
          </span>
          <span className="flex items-center gap-1.5">
            <Check className="w-4 h-4 text-emerald-400" /> Free 14-day trial
          </span>
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-[#8B5CF6]" /> SOC2 Compliant & Encrypted
          </span>
        </div>

      </div>
    </section>
  );
};

