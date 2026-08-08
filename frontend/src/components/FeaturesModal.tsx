import React, { useState } from 'react';
import { X, Mic, FileText, CheckSquare, MessageSquare, Search, Users, History, Sparkles, ArrowRight, Zap, Check } from 'lucide-react';

interface FeaturesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenGetStarted: () => void;
}

export const FeaturesModal: React.FC<FeaturesModalProps> = ({ isOpen, onClose, onOpenGetStarted }) => {
  const [selectedFeature, setSelectedFeature] = useState<number>(0);

  if (!isOpen) return null;

  const features = [
    {
      id: 'transcription',
      title: 'AI Transcription',
      icon: Mic,
      tag: '99.2% Accuracy',
      color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
      description: 'Powered by Whisper HD, our transcription engine converts raw meeting audio into crystal-clear text with automatic speaker diarization and background noise elimination.',
      bullets: [
        'Multi-speaker identification with custom avatar tags',
        'Word-level timestamps for pinpoint navigation',
        'Noise cancellation filtering out keyboard clatter & crosstalk',
        'Multi-language transcription supporting 32+ global languages'
      ],
      previewSnippet: {
        speaker: 'Sarah Chen (Lead Architect)',
        time: '18:24',
        quote: 'We will migrate the JWT refresh token service to OAuth 2.1 PKCE standards by Friday.'
      }
    },
    {
      id: 'summaries',
      title: 'Smart Summaries',
      icon: FileText,
      tag: '30-Sec Read',
      color: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
      description: 'Condenses 60-minute meetings into structured 30-second executive summaries highlighting critical decisions, key arguments, and technical consensus.',
      bullets: [
        'Executive overview paragraphs generated in real-time',
        'Key takeaways categorized by topic & priority',
        'Instant Markdown & PDF export for Notion & Confluence',
        'Custom summary templates tailored to Engineering, Product, or Sales'
      ],
      previewSnippet: {
        speaker: 'AI Summary Engine',
        time: '30s Read',
        quote: 'Key Decision: Shift authentication architecture to OAuth 2.1 PKCE with Redis token blacklist caching.'
      }
    },
    {
      id: 'action-items',
      title: 'Action Items',
      icon: CheckSquare,
      tag: 'Auto-Parsed',
      color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
      description: 'Automatically detects task commitments in spoken language, assigns them to team members, sets realistic deadlines, and syncs directly to Linear and Jira.',
      bullets: [
        'Spoken intent parsing ("I will take ownership of...")',
        'Assignee mapping via voice signature & name matching',
        'Priority tagging (High, Medium, Low)',
        'Direct 1-click sync to Linear, Jira, and Asana'
      ],
      previewSnippet: {
        speaker: 'Task Auto-Detector',
        time: 'Synced to Linear',
        quote: 'Task: "Complete OAuth 2.1 authentication flow" -> Assigned to Sarah Chen (Due Friday)'
      }
    },
    {
      id: 'ai-chat',
      title: 'AI Chat',
      icon: MessageSquare,
      tag: 'Context Aware',
      color: 'text-sky-400 bg-sky-500/10 border-sky-500/20',
      description: 'Ask any question about current or past meetings. Get instant answers with cited audio timestamps so you can verify the exact spoken quote.',
      bullets: [
        'Ask "What did Alex say about the roadmap deadline?"',
        'Cited timestamp jump links (@18:24)',
        'Multi-turn conversational follow-ups',
        'No halluncinations — answers strictly grounded in audio transcript'
      ],
      previewSnippet: {
        speaker: 'MeetPilot Assistant',
        time: 'Cited @18:24',
        quote: 'Alex confirmed the Q3 auth refactor deadline is set for Friday at 5:00 PM.'
      }
    },
    {
      id: 'semantic-search',
      title: 'Semantic Search',
      icon: Search,
      tag: 'pgvector <10ms',
      color: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
      description: 'Search across thousands of hours of historical team meetings using natural language. Finds exact topics even if exact keywords were not used.',
      bullets: [
        'PostgreSQL pgvector hybrid BM25 + dense embedding index',
        'Cross-meeting querying across all workspace archives',
        'Filter by date, speaker, topic tag, or project folder',
        'Sub-10ms response time at scale'
      ],
      previewSnippet: {
        speaker: 'Vector Index',
        time: '4ms latency',
        quote: 'Found 14 relevant discussion moments regarding "OAuth authentication security".'
      }
    },
    {
      id: 'team-workspace',
      title: 'Team Workspace',
      icon: Users,
      tag: 'SOC2 Encrypted',
      color: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
      description: 'Collaborate with your entire company. Share meeting notes, assign cross-team action items, and manage granular workspace access permissions.',
      bullets: [
        'Granular role permissions (Admin, Editor, Viewer)',
        'Project-based meeting tag folders',
        'Encrypted team meeting archives',
        'Activity notifications & Slack digest webhooks'
      ],
      previewSnippet: {
        speaker: 'Acme Workspace',
        time: 'Active Team',
        quote: '48 active members across Product, Engineering, and DevOps.'
      }
    },
    {
      id: 'meeting-history',
      title: 'Meeting History',
      icon: History,
      tag: 'Permanent Memory',
      color: 'text-teal-400 bg-teal-500/10 border-teal-500/20',
      description: 'A searchable calendar and archive of every team meeting. Review timeline chapters, play audio clips, and track historical decisions.',
      bullets: [
        'Interactive calendar timeline layout',
        'Audio clip playback with synced transcript highlighting',
        'Decisions decision log archive',
        '1-click export to PDF, Markdown, and JSON'
      ],
      previewSnippet: {
        speaker: 'History Vault',
        time: '142 Meetings',
        quote: '100% indexed and archived for permanent workspace context.'
      }
    }
  ];

  const active = features[selectedFeature];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-5xl rounded-2xl bg-[#0e101c] border border-white/20 p-6 sm:p-8 shadow-2xl text-slate-200 max-h-[90vh] overflow-y-auto space-y-6">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#111113] border border-[#27272A] text-[#8B5CF6] text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-[#8B5CF6]" />
            <span>Complete Feature Capabilities</span>
          </div>

          <h3 className="text-3xl font-extrabold text-white">
            Everything You Need to Master Meetings
          </h3>

          <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto">
            Click on any feature below to inspect its detailed technical capabilities.
          </p>
        </div>

        {/* Features Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-2">
          
          {/* Left Feature Selector (5 cols) */}
          <div className="lg:col-span-5 space-y-2">
            {features.map((item, idx) => {
              const IconComp = item.icon;
              const isSel = selectedFeature === idx;
              return (
                <div
                  key={item.id}
                  onClick={() => setSelectedFeature(idx)}
                  className={`p-3.5 rounded-xl cursor-pointer transition-all border flex items-center justify-between ${
                    isSel
                      ? 'bg-[#18181b] border-[#8B5CF6] shadow-lg shadow-[#8B5CF6]/10'
                      : 'bg-[#111113] border-[#27272A] hover:bg-[#18181b] hover:border-[#27272A]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${item.color}`}>
                      <IconComp className="w-4 h-4" />
                    </div>
                    <div>
                      <div className={`text-xs font-bold ${isSel ? 'text-[#8B5CF6]' : 'text-white'}`}>
                        {item.title}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {item.tag}
                      </div>
                    </div>
                  </div>

                  <ArrowRight className={`w-4 h-4 transition-transform ${isSel ? 'text-[#8B5CF6] translate-x-0.5' : 'text-slate-600'}`} />
                </div>
              );
            })}
          </div>

          {/* Right Active Feature Inspector (7 cols) */}
          <div className="lg:col-span-7 flex flex-col justify-between p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono px-2.5 py-1 rounded bg-[#8B5CF6]/20 text-[#8B5CF6] font-bold uppercase">
                    {active.tag}
                  </span>
                </div>
                <span className="text-xs text-slate-500 font-mono">Feature 0{selectedFeature + 1} / 07</span>
              </div>

              <h4 className="text-2xl font-extrabold text-white flex items-center gap-2">
                {active.title}
              </h4>

              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                {active.description}
              </p>

              <div className="space-y-2 pt-2 border-t border-[#27272A]">
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Key Capabilities</div>
                <div className="grid grid-cols-1 gap-2">
                  {active.bullets.map((b, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-slate-300">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      <span>{b}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sample Output Simulator box */}
              <div className="p-4 rounded-xl bg-[#18181b] border border-[#27272A] space-y-2 font-mono text-xs">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-[#8B5CF6] font-bold">{active.previewSnippet.speaker}</span>
                  <span className="text-slate-500">{active.previewSnippet.time}</span>
                </div>
                <p className="text-slate-300 italic text-[11px]">
                  "{active.previewSnippet.quote}"
                </p>
              </div>
            </div>

            <button
              onClick={() => { onClose(); onOpenGetStarted(); }}
              className="w-full py-3 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] text-white font-bold text-xs flex items-center justify-center gap-2 transition-all cursor-pointer shadow-lg shadow-[#8B5CF6]/20"
            >
              <span>Try {active.title} Free in Workspace</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

        </div>

      </div>
    </div>
  );
};
