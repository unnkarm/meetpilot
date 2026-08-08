import React, { useState, useEffect } from 'react';
import { Sparkles, Send, User } from 'lucide-react';

export const AIChatDemo: React.FC = () => {
  const [activeQuestion, setActiveQuestion] = useState('Who is building authentication?');
  const [displayedAnswer, setDisplayedAnswer] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const sampleQueries = [
    {
      q: 'Who is building authentication?',
      person: 'Sarah Chen',
      deadline: 'Friday at 5:00 PM',
      timestamp: '18:42',
      confidence: '97%',
      details: 'Sarah is assigned to lead the OAuth 2.1 authorization server migration and session cookie refactor.'
    },
    {
      q: 'What were the major decisions regarding database scaling?',
      person: 'David Kim',
      deadline: 'Next Sprint (Monday)',
      timestamp: '24:15',
      confidence: '99%',
      details: 'Agreed to migrate from single PostgreSQL instance to Read Replicas on Cloud SQL with connection pooling.'
    },
    {
      q: 'When is the mobile app beta expected to launch?',
      person: 'Elena Rostova',
      deadline: 'October 15th',
      timestamp: '32:10',
      confidence: '95%',
      details: 'TestFlight build release is scheduled for external beta testers following security audit sign-off.'
    }
  ];

  const currentData = sampleQueries.find(s => s.q === activeQuestion) || sampleQueries[0];

  useEffect(() => {
    setIsTyping(true);
    setDisplayedAnswer('');
    let index = 0;
    const textToType = currentData.details;

    const timer = setInterval(() => {
      setDisplayedAnswer(textToType.slice(0, index));
      index++;
      if (index > textToType.length) {
        setIsTyping(false);
        clearInterval(timer);
      }
    }, 25);

    return () => clearInterval(timer);
  }, [activeQuestion]);

  return (
    <section className="py-20 lg:py-28 relative overflow-hidden bg-[#09090B] border-t border-[#27272A]">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 space-y-12">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#111113] border border-[#27272A] text-[#8B5CF6] text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-[#8B5CF6]" />
            <span>Raycast-Style Natural Language AI</span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-extrabold text-[#FAFAFA] tracking-tight">
            Ask your meeting anything.
          </h2>

          <p className="text-slate-400 text-base sm:text-lg">
            Stop scrubbing through 60-minute audio recordings. Query your workspace in plain English with instant source verification.
          </p>
        </div>

        {/* ChatGPT / Raycast Style Interactive Terminal Container */}
        <div className="rounded-2xl bg-[#111113] border border-[#27272A] shadow-2xl p-6 sm:p-8 space-y-6 relative overflow-hidden">
          
          {/* Preset Buttons */}
          <div className="flex flex-wrap items-center gap-2 pb-4 border-b border-[#27272A]">
            <span className="text-xs font-mono text-slate-500 mr-2">Try query:</span>
            {sampleQueries.map((sq, idx) => (
              <button
                key={idx}
                onClick={() => setActiveQuestion(sq.q)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer ${
                  activeQuestion === sq.q
                    ? 'bg-[#8B5CF6] text-white shadow-md shadow-[#8B5CF6]/30'
                    : 'bg-[#18181b] text-slate-400 border border-[#27272A] hover:border-[#8B5CF6]/40 hover:text-white'
                }`}
              >
                "{sq.q}"
              </button>
            ))}
          </div>

          {/* Simulated User Question Bubble */}
          <div className="flex items-start gap-3 p-4 rounded-xl bg-[#18181b] border border-[#27272A]">
            <div className="w-7 h-7 rounded-lg bg-[#27272A] text-slate-300 flex items-center justify-center shrink-0">
              <User className="w-4 h-4" />
            </div>
            <div className="space-y-1">
              <div className="text-[11px] font-mono text-slate-500">Query</div>
              <div className="text-sm font-semibold text-[#FAFAFA]">{activeQuestion}</div>
            </div>
          </div>

          {/* AI Response Card with Exact Spec Metrics */}
          <div className="p-6 rounded-2xl bg-[#18181b] border border-[#8B5CF6]/40 space-y-6 shadow-xl relative">
            
            <div className="flex items-center justify-between pb-3 border-b border-[#27272A]">
              <div className="flex items-center gap-2 font-bold text-sm text-[#FAFAFA]">
                <Sparkles className="w-4 h-4 text-[#8B5CF6]" />
                <span>MeetPilot AI Answer</span>
              </div>
              <span className="text-xs font-mono px-2.5 py-0.5 rounded bg-[#8B5CF6]/20 text-[#8B5CF6] border border-[#8B5CF6]/30">
                Confidence: {currentData.confidence}
              </span>
            </div>

            {/* Spec Output Grid: Person, Deadline, Timestamp, Confidence */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-[#111113] border border-[#27272A]">
                <div className="text-[10px] uppercase font-mono text-slate-500">Owner</div>
                <div className="text-sm font-bold text-[#FAFAFA] mt-0.5">{currentData.person}</div>
              </div>

              <div className="p-3 rounded-xl bg-[#111113] border border-[#27272A]">
                <div className="text-[10px] uppercase font-mono text-slate-500">Deadline</div>
                <div className="text-sm font-bold text-emerald-400 mt-0.5">{currentData.deadline}</div>
              </div>

              <div className="p-3 rounded-xl bg-[#111113] border border-[#27272A]">
                <div className="text-[10px] uppercase font-mono text-slate-500">Mentioned</div>
                <div className="text-sm font-mono font-bold text-[#3B82F6] mt-0.5">@{currentData.timestamp}</div>
              </div>

              <div className="p-3 rounded-xl bg-[#111113] border border-[#27272A]">
                <div className="text-[10px] uppercase font-mono text-slate-500">Accuracy</div>
                <div className="text-sm font-bold text-[#8B5CF6] mt-0.5">{currentData.confidence} Verified</div>
              </div>
            </div>

            {/* Typing text output */}
            <div className="text-sm text-slate-300 leading-relaxed font-sans pt-2">
              <span>{displayedAnswer}</span>
              {isTyping && <span className="w-2 h-4 bg-[#8B5CF6] inline-block ml-1 animate-cursor"></span>}
            </div>

          </div>

          {/* Interactive Prompt Bar */}
          <div className="flex items-center gap-3 pt-2">
            <input
              type="text"
              value={activeQuestion}
              onChange={(e) => setActiveQuestion(e.target.value)}
              placeholder="Type any question about your recordings..."
              className="flex-1 bg-[#18181b] border border-[#27272A] rounded-xl px-4 py-3 text-sm text-[#FAFAFA] placeholder-slate-500 focus:outline-none focus:border-[#8B5CF6]"
            />
            <button className="px-5 py-3 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] text-white font-bold text-sm flex items-center gap-2 transition-colors cursor-pointer">
              <span>Ask</span>
              <Send className="w-4 h-4" />
            </button>
          </div>

        </div>

      </div>
    </section>
  );
};

