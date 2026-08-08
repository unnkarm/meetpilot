import React from 'react';
import { TECH_STACK } from '../data/landingData';
import { Sparkles, Zap, Globe, Database, Cpu, Box } from 'lucide-react';

export const TrustedBy: React.FC = () => {
  const getIcon = (iconName: string, color: string) => {
    switch (iconName) {
      case 'Sparkles': return <Sparkles className={`w-4 h-4 ${color}`} />;
      case 'Zap': return <Zap className={`w-4 h-4 ${color}`} />;
      case 'Globe': return <Globe className={`w-4 h-4 ${color}`} />;
      case 'Database': return <Database className={`w-4 h-4 ${color}`} />;
      case 'Cpu': return <Cpu className={`w-4 h-4 ${color}`} />;
      case 'Box': return <Box className={`w-4 h-4 ${color}`} />;
      default: return <Sparkles className={`w-4 h-4 ${color}`} />;
    }
  };

  return (
    <section className="py-12 border-y border-[#27272A] bg-[#09090B] relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
        
        <div className="flex items-center justify-center gap-2">
          <span className="h-px w-8 bg-gradient-to-r from-transparent to-slate-700"></span>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
            Engineered with Production-Grade Infrastructure
          </p>
          <span className="h-px w-8 bg-gradient-to-l from-transparent to-slate-700"></span>
        </div>

        {/* Tech Stack Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 sm:gap-6 pt-2">
          {TECH_STACK.map((tech) => (
            <div
              key={tech.name}
              className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-[#8B5CF6]/50 hover:bg-white/[0.05] transition-all duration-300 flex flex-col items-center justify-center gap-2 group shadow-sm hover:shadow-indigo-500/10"
            >
              <div className="p-2 rounded-lg bg-white/[0.04] group-hover:scale-110 transition-transform">
                {getIcon(tech.iconName, tech.color)}
              </div>
              <div className="text-center">
                <div className="text-sm font-bold text-white tracking-wide group-hover:text-indigo-300 transition-colors">
                  {tech.name}
                </div>
                <div className="text-[10px] text-slate-400 leading-tight mt-0.5 font-sans">
                  {tech.role}
                </div>
              </div>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
};
