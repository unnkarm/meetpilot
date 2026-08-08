import React, { useState } from 'react';
import { X, BookOpen, Code, Terminal, Zap, Check, Copy } from 'lucide-react';

interface DocsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DocsDrawer: React.FC<DocsDrawerProps> = ({ isOpen, onClose }) => {
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const [activeTab, setActiveTab] = useState<'quickstart' | 'webhooks' | 'whisper'>('quickstart');

  if (!isOpen) return null;

  const codeSnippets = {
    quickstart: `import { MeetPilot } from '@meetpilot/sdk';

const meetpilot = new MeetPilot({ apiKey: process.env.MEETPILOT_API_KEY });

// Upload and analyze meeting audio file
const meeting = await meetpilot.meetings.process({
  fileUrl: 'https://cdn.example.com/sprint_planning.mp3',
  title: 'Weekly Sprint Planning',
  extractTasks: true,
  generateSummary: true
});

console.log(meeting.summary);
console.log(meeting.tasks);`,
    webhooks: `// Webhook payload received when meeting analysis completes
{
  "event": "meeting.processed",
  "data": {
    "meetingId": "mp_9281238",
    "title": "Weekly Sprint Planning",
    "tasksExtracted": 12,
    "decisionsCaptured": 5,
    "summaryUrl": "https://app.meetpilot.ai/m/mp_9281238"
  }
}`,
    whisper: `// Custom speaker diarization query API
const transcript = await meetpilot.transcript.search({
  meetingId: 'mp_9281238',
  query: 'authentication refactor',
  minConfidence: 0.95
});`
  };

  const handleCopy = () => {
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-2xl bg-[#090b13] border-l border-white/20 p-6 sm:p-8 h-full overflow-y-auto text-slate-200 flex flex-col justify-between">
        
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-6">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white">
                <BookOpen className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">MeetPilot AI Documentation</h3>
                <p className="text-xs text-slate-400">REST API & Node.js SDK Reference v2.4</p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation tabs */}
          <div className="flex items-center gap-2 mb-6 border-b border-white/10 pb-3">
            <button
              onClick={() => setActiveTab('quickstart')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                activeTab === 'quickstart' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              SDK Quickstart
            </button>
            <button
              onClick={() => setActiveTab('webhooks')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                activeTab === 'webhooks' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Webhooks
            </button>
            <button
              onClick={() => setActiveTab('whisper')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                activeTab === 'whisper' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Whisper Search
            </button>
          </div>

          {/* Code Viewer Box */}
          <div className="rounded-xl bg-[#05060b] border border-white/10 p-4 relative font-mono text-xs">
            <div className="flex items-center justify-between text-slate-400 text-[11px] pb-3 border-b border-white/10 mb-3">
              <span className="flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                {activeTab === 'quickstart' && 'app.ts'}
                {activeTab === 'webhooks' && 'webhook-payload.json'}
                {activeTab === 'whisper' && 'search.ts'}
              </span>

              <button
                onClick={handleCopy}
                className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors"
              >
                {copiedSnippet ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedSnippet ? 'Copied!' : 'Copy Code'}</span>
              </button>
            </div>

            <pre className="text-indigo-200 overflow-x-auto leading-relaxed">
              <code>{codeSnippets[activeTab]}</code>
            </pre>
          </div>

          {/* API Info cards */}
          <div className="mt-6 space-y-3">
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10 space-y-1">
              <div className="text-xs font-bold text-white flex items-center gap-2">
                <Zap className="w-4 h-4 text-indigo-400" /> Sub-10ms Vector Indexing
              </div>
              <p className="text-xs text-slate-400">
                PostgreSQL pgvector backend ensures queries run at edge latency.
              </p>
            </div>
          </div>
        </div>

        <div className="pt-6 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
          <span>Need custom API scope?</span>
          <a href="mailto:support@meetpilot.ai" className="text-indigo-400 hover:underline">Contact Dev Team</a>
        </div>

      </div>
    </div>
  );
};
