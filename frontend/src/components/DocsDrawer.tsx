import { useState } from 'react';
import { X, BookOpen, Terminal, Check, Copy } from 'lucide-react';

interface DocsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

const snippets = {
  startup: `# From the repository root (PowerShell)
$env:OLLAMA_URL = "http://ollama:11434"
docker compose --profile local-ai up -d ollama
docker compose exec ollama ollama pull qwen2.5:1.5b
docker compose exec ollama ollama pull nomic-embed-text
docker compose --profile local-ai up --build -d

# Configure Clerk in backend/.env and frontend/.env first.`,
  meetings: `# Send a Clerk session JWT as a Bearer token.
# POST /api/v1/meetings/upload is multipart/form-data:
#   workspace_id: UUID
#   title: meeting title
#   file: supported audio recording
#
# GET /api/v1/meetings/{meeting_id}
# GET /api/v1/meetings/{meeting_id}/transcript
# GET /api/v1/meetings/{meeting_id}/summary
# GET /api/v1/meetings/{meeting_id}/tasks
# GET /api/v1/meetings/{meeting_id}/decisions
# POST /api/v1/meetings/{meeting_id}/retry`,
  knowledge: `# Authenticated workspace knowledge routes:
# POST /api/v1/documents/upload
#   multipart: workspace_id, file
#
# POST /api/v1/knowledge/chat
#   JSON: {"workspace_id": "<UUID>", "question": "What did we decide?"}
#
# Answers include citations to retrieved workspace sources.`
};

type Tab = keyof typeof snippets;

export const DocsDrawer = ({ isOpen, onClose }: DocsDrawerProps) => {
  const [activeTab, setActiveTab] = useState<Tab>('startup');
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  if (!isOpen) return null;

  const copySnippet = async () => {
    try {
      await navigator.clipboard.writeText(snippets[activeTab]);
      setCopiedSnippet(true);
      window.setTimeout(() => setCopiedSnippet(false), 2000);
    } catch {
      setCopiedSnippet(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div role="dialog" aria-modal="true" aria-label="MeetPilot documentation" className="w-full max-w-2xl bg-[#090b13] border-l border-white/20 p-6 sm:p-8 h-full overflow-y-auto text-slate-200 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-6">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white"><BookOpen className="w-5 h-5" /></div>
              <div>
                <h3 className="text-lg font-bold text-white">MeetPilot Local Beta</h3>
                <p className="text-xs text-slate-400">Verified setup and API entry points</p>
              </div>
            </div>
            <button onClick={onClose} aria-label="Close documentation" className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors"><X className="w-5 h-5" /></button>
          </div>

          <div className="flex items-center gap-2 mb-6 border-b border-white/10 pb-3">
            {(['startup', 'meetings', 'knowledge'] as Tab[]).map((tab) => (
              <button key={tab} onClick={() => setActiveTab(tab)} className={'px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-colors ' + (activeTab === tab ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white')}>
                {tab}
              </button>
            ))}
          </div>

          <div className="rounded-xl bg-[#05060b] border border-white/10 p-4 relative font-mono text-xs">
            <div className="flex items-center justify-between text-slate-400 text-[11px] pb-3 border-b border-white/10 mb-3">
              <span className="flex items-center gap-1.5"><Terminal className="w-3.5 h-3.5 text-indigo-400" /> {activeTab}.txt</span>
              <button onClick={copySnippet} className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors">
                {copiedSnippet ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedSnippet ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <pre className="text-indigo-200 overflow-x-auto leading-relaxed"><code>{snippets[activeTab]}</code></pre>
          </div>
          <p className="mt-5 text-xs text-slate-400">FastAPI serves the full interactive schema at <a className="text-indigo-400 hover:underline" href="http://localhost:8000/docs" target="_blank" rel="noreferrer">localhost:8000/docs</a>. Authentication and workspace membership are required for data routes.</p>
        </div>
        <div className="pt-6 mt-8 border-t border-white/10 text-xs text-slate-500">The README in this repository has full configuration, verification commands, and current limitations.</div>
      </div>
    </div>
  );
};
