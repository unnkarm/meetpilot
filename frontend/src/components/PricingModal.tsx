import React, { useState } from 'react';
import { X, Check, Sparkles, Zap, Shield, ArrowRight } from 'lucide-react';

interface PricingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenGetStarted: () => void;
}

export const PricingModal: React.FC<PricingModalProps> = ({ isOpen, onClose, onOpenGetStarted }) => {
  const [annualBilling, setAnnualBilling] = useState(true);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-4xl rounded-2xl bg-[#0e101c] border border-white/20 p-6 sm:p-8 shadow-2xl text-slate-200 max-h-[90vh] overflow-y-auto">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="text-center space-y-3 mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Pricing Plans — Coming Soon</span>
          </div>

          <h3 className="text-3xl font-extrabold text-white">
            Simple, Transparent Pricing
          </h3>

          <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto">
            Choose the right plan for your team. Start free with 14-day full platform access.
          </p>

          {/* Billing Switch */}
          <div className="flex items-center justify-center gap-3 pt-2">
            <span className={`text-xs font-semibold ${!annualBilling ? 'text-white' : 'text-slate-400'}`}>Monthly</span>
            <button
              onClick={() => setAnnualBilling(!annualBilling)}
              className="w-12 h-6 rounded-full bg-indigo-950 border border-indigo-500/40 p-1 flex items-center transition-colors"
            >
              <div className={`w-4 h-4 rounded-full bg-indigo-400 transition-transform ${annualBilling ? 'translate-x-6 bg-indigo-300' : 'translate-x-0'}`} />
            </button>
            <span className={`text-xs font-semibold flex items-center gap-1.5 ${annualBilling ? 'text-white' : 'text-slate-400'}`}>
              Annual <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Save 20%</span>
            </span>
          </div>
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Starter Plan */}
          <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 flex flex-col justify-between space-y-6">
            <div className="space-y-4">
              <div className="text-sm font-bold uppercase tracking-wider text-slate-400">Starter</div>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-extrabold text-white">$0</span>
                <span className="text-xs text-slate-400">/ forever free</span>
              </div>
              <p className="text-xs text-slate-400">Perfect for individual developers and small team tests.</p>

              <ul className="space-y-2.5 text-xs text-slate-300 pt-2 border-t border-white/5">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>300 meeting minutes / mo</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>AI Summaries & Tasks</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>7-day meeting history</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => { onClose(); onOpenGetStarted(); }}
              className="w-full py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 font-semibold text-xs text-slate-200 transition-colors"
            >
              Get Started Free
            </button>
          </div>

          {/* Pro Plan (Highlighted) */}
          <div className="p-6 rounded-2xl bg-indigo-950/40 border-2 border-indigo-500 shadow-xl shadow-indigo-500/20 flex flex-col justify-between space-y-6 relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-bold text-[10px] tracking-wider uppercase">
              Most Popular
            </div>

            <div className="space-y-4">
              <div className="text-sm font-bold uppercase tracking-wider text-indigo-300">Pro Team</div>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-extrabold text-white">
                  ${annualBilling ? '19' : '24'}
                </span>
                <span className="text-xs text-slate-400">/ user / mo</span>
              </div>
              <p className="text-xs text-indigo-200">For scaling engineering & product teams.</p>

              <ul className="space-y-2.5 text-xs text-slate-200 pt-2 border-t border-white/10">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Unlimited meeting minutes</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Speaker Diarization & Vector Search</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Linear & Jira Auto Task Sync</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Permanent Meeting Memory</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => { onClose(); onOpenGetStarted(); }}
              className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 transition-colors flex items-center justify-center gap-1.5"
            >
              <span>Reserve Pro Seat</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Enterprise Plan */}
          <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 flex flex-col justify-between space-y-6">
            <div className="space-y-4">
              <div className="text-sm font-bold uppercase tracking-wider text-slate-400">Enterprise</div>
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-extrabold text-white">Custom</span>
              </div>
              <p className="text-xs text-slate-400">Dedicated cloud deployment, custom SLA & SOC2 audits.</p>

              <ul className="space-y-2.5 text-xs text-slate-300 pt-2 border-t border-white/5">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Custom LLM & On-Prem RAG</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>SAML SSO & Okta Integration</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Dedicated Support Engineer</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => { onClose(); onOpenGetStarted(); }}
              className="w-full py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 font-semibold text-xs text-slate-200 transition-colors"
            >
              Contact Sales
            </button>
          </div>

        </div>

      </div>
    </div>
  );
};
