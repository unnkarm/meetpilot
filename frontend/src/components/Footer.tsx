import React from 'react';
import { Bot, Github, Heart } from 'lucide-react';

interface FooterProps {
  onOpenPrivacy: () => void;
  onOpenDocs: () => void;
  onOpenPricing: () => void;
}

export const Footer: React.FC<FooterProps> = ({ onOpenPrivacy, onOpenDocs, onOpenPricing }) => {
  const scrollTo = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <footer className="bg-[#09090B] border-t border-[#27272A] pt-16 pb-12 text-slate-400 text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 pb-12 border-b border-[#27272A]">
          
          {/* Brand Info */}
          <div className="md:col-span-5 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-[#8B5CF6] p-[1px]">
                <div className="w-full h-full bg-[#111113] rounded-[11px] flex items-center justify-center">
                  <Bot className="w-4 h-4 text-[#8B5CF6]" />
                </div>
              </div>
              <span className="font-extrabold text-lg text-[#FAFAFA] tracking-tight">MeetPilot AI</span>
            </div>

            <p className="text-slate-400 max-w-sm leading-relaxed">
              The AI meeting intelligence platform that turns team conversations into searchable transcripts, concise summaries, and automated task execution.
            </p>

            <div className="text-slate-500 text-[11px] font-mono">
              Engineered for privacy, compliance & zero-latency RAG search.
            </div>
          </div>

          {/* Links Column 1 */}
          <div className="md:col-span-3 space-y-3">
            <div className="font-bold text-[#FAFAFA] text-xs uppercase tracking-wider">Product</div>
            <ul className="space-y-2">
              <li>
                <button onClick={() => scrollTo('features')} className="hover:text-white transition-colors cursor-pointer">Features</button>
              </li>
              <li>
                <button onClick={() => scrollTo('how-it-works')} className="hover:text-white transition-colors cursor-pointer">How it Works</button>
              </li>
              <li>
                <button onClick={() => scrollTo('dashboard-preview')} className="hover:text-white transition-colors cursor-pointer">Live Workspace</button>
              </li>
              <li>
                <button onClick={onOpenPricing} className="hover:text-white transition-colors flex items-center gap-1 cursor-pointer">
                  <span>Pricing</span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-white/10 text-slate-300 font-mono">Soon</span>
                </button>
              </li>
            </ul>
          </div>

          {/* Links Column 2 */}
          <div className="md:col-span-2 space-y-3">
            <div className="font-bold text-[#FAFAFA] text-xs uppercase tracking-wider">Resources</div>
            <ul className="space-y-2">
              <li>
                <button onClick={onOpenDocs} className="hover:text-white transition-colors cursor-pointer">Docs & API</button>
              </li>
              <li>
                <button onClick={onOpenPrivacy} className="hover:text-white transition-colors cursor-pointer">Privacy Policy</button>
              </li>
              <li>
                <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors flex items-center gap-1">
                  <Github className="w-3.5 h-3.5" />
                  <span>GitHub Repository</span>
                </a>
              </li>
            </ul>
          </div>

          {/* Links Column 3 */}
          <div className="md:col-span-2 space-y-3">
            <div className="font-bold text-[#FAFAFA] text-xs uppercase tracking-wider">Security</div>
            <ul className="space-y-2 text-slate-400">
              <li>SOC2 Type II Certified</li>
              <li>256-bit AES Encryption</li>
              <li>GDPR Compliant</li>
            </ul>
          </div>

        </div>

        {/* Bottom Bar */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-slate-500">
          <div>
            © {new Date().getFullYear()} MeetPilot AI Inc. All rights reserved.
          </div>

          <div className="flex items-center gap-1 text-slate-400">
            <span>Made with</span>
            <Heart className="w-3.5 h-3.5 text-red-500 fill-red-500 mx-0.5 animate-pulse" />
            <span>for modern teams everywhere.</span>
          </div>
        </div>

      </div>
    </footer>
  );
};

