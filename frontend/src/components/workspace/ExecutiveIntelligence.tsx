import React from 'react';
import {
  FileText,
  CheckCircle2,
  ChevronRight,
  Sparkles,
  ShieldCheck,
  Play,
  ArrowRight,
} from 'lucide-react';
import { ApiMeetingSummary, ApiDecision } from '../../types';
import { formatTimeSeconds } from '../../utils/speakerUtils';

interface ExecutiveIntelligenceProps {
  summary?: ApiMeetingSummary | null;
  decisions: ApiDecision[];
  onSeek: (seconds: number) => void;
}

export const ExecutiveIntelligence: React.FC<ExecutiveIntelligenceProps> = ({
  summary,
  decisions,
  onSeek,
}) => {
  const parseTimestampSeconds = (ts?: string | null): number | null => {
    if (!ts) return null;
    const parts = ts.replace('@', '').split(':').map(Number);
    if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
      return parts[0] * 60 + parts[1];
    }
    const single = Number(ts);
    return !isNaN(single) ? single : null;
  };

  return (
    <div className="space-y-6">
      {/* 1. Main Grid: Executive Summary & Key Takeaways + Decisions */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left (7 cols): Executive Summary & Key Takeaways */}
        <div className="lg:col-span-7 space-y-6">
          {/* Executive Overview Card */}
          <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-3.5 shadow-xl">
            <div className="flex items-center justify-between pb-2 border-b border-[#27272A]">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#8B5CF6]" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Executive Summary
                </h3>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-400">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Single-Pass Synthesis</span>
              </div>
            </div>

            <p className="text-xs sm:text-sm text-slate-200 leading-relaxed bg-[#18181b] p-4 rounded-xl border border-[#27272A] font-normal">
              {summary?.overview || 'Meeting synthesis is being prepared...'}
            </p>

            <div className="flex items-center gap-2 text-[11px] text-slate-500 italic">
              <Sparkles className="w-3 h-3 text-[#8B5CF6]" />
              <span>Grounded in speech transcript · Click timestamps to verify source audio.</span>
            </div>
          </div>

          {/* Key Takeaways */}
          <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-3.5 shadow-xl">
            <div className="flex items-center gap-2 pb-2 border-b border-[#27272A]">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                Key Takeaways
              </h3>
            </div>

            {summary?.key_takeaways && summary.key_takeaways.length > 0 ? (
              <div className="space-y-2.5">
                {summary.key_takeaways.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 text-xs sm:text-sm text-slate-200 bg-[#18181b] p-3.5 rounded-xl border border-[#27272A] hover:border-[#8B5CF6]/30 transition-colors"
                  >
                    <span className="w-5 h-5 rounded-full bg-emerald-500/15 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                      ✓
                    </span>
                    <span className="leading-relaxed">{item}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic p-4 bg-[#18181b] rounded-xl">
                No explicit key takeaways noted in this session.
              </p>
            )}
          </div>

          {/* Next Steps */}
          {summary?.next_steps && summary.next_steps.length > 0 && (
            <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-3.5 shadow-xl">
              <div className="flex items-center gap-2 pb-2 border-b border-[#27272A]">
                <ArrowRight className="w-4 h-4 text-[#8B5CF6]" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Next Steps
                </h3>
              </div>

              <div className="space-y-2.5">
                {summary.next_steps.map((step, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 text-xs sm:text-sm text-slate-200 bg-[#18181b] p-3.5 rounded-xl border border-[#27272A] hover:border-[#8B5CF6]/30 transition-colors"
                  >
                    <ChevronRight className="w-4 h-4 text-[#8B5CF6] shrink-0 mt-0.5" />
                    <span className="leading-relaxed">{step}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right (5 cols): Consensus Decisions Log */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4 shadow-xl">
            <div className="flex items-center justify-between pb-2 border-b border-[#27272A]">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Consensus Decisions ({decisions.length})
                </h3>
              </div>
              <span className="text-[10px] font-mono text-slate-500">Agreed outcomes</span>
            </div>

            {decisions.length === 0 ? (
              <div className="p-8 text-center border border-dashed border-[#27272A] rounded-xl space-y-2">
                <p className="text-xs text-slate-400">
                  No consensus decisions were detected in this meeting.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {decisions.map((d) => {
                  const seekSecs = parseTimestampSeconds(d.transcript_timestamp);
                  return (
                    <div
                      key={d.id}
                      className="p-4 rounded-xl bg-[#18181b] border border-[#27272A] space-y-2 hover:border-amber-500/40 transition-colors shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-xs font-bold text-amber-300 leading-snug">
                          {d.topic}
                        </span>

                        {d.transcript_timestamp && seekSecs !== null && (
                          <button
                            onClick={() => onSeek(seekSecs)}
                            title="Jump audio to when this was decided"
                            className="text-[10px] font-mono text-amber-400 hover:text-white bg-amber-500/10 hover:bg-amber-500 px-2 py-0.5 rounded-lg border border-amber-500/20 transition-colors cursor-pointer shrink-0 flex items-center gap-1 font-semibold"
                          >
                            <Play className="w-2.5 h-2.5 fill-current" />
                            <span>@{d.transcript_timestamp.replace('@', '')}</span>
                          </button>
                        )}
                      </div>

                      <p className="text-xs text-slate-300 leading-relaxed">{d.outcome}</p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
