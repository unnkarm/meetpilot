import React, { useState, useRef, useEffect } from 'react';
import {
  Brain,
  Upload,
  FileText,
  Trash2,
  Send,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  FileCode,
  FileSpreadsheet,
  HelpCircle,
  ExternalLink,
  ChevronRight,
  Plus,
  BookOpen,
  Mic,
  Calendar,
} from 'lucide-react';
import {
  ApiKnowledgeDocument,
  ApiKnowledgeCitation,
  ApiKnowledgeChatMessage,
  ApiWorkspace,
} from '../../types';
import {
  useWorkspaceDocuments,
  uploadDocumentApi,
  deleteDocumentApi,
  sendKnowledgeChatApi,
} from '../../services/api';

interface AIKnowledgeViewProps {
  activeWorkspace: ApiWorkspace | null;
  getToken: () => Promise<string | null>;
  onNavigateToMeeting?: (meetingId: string, timestampSeconds?: number) => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export const AIKnowledgeView: React.FC<AIKnowledgeViewProps> = ({
  activeWorkspace,
  getToken,
  onNavigateToMeeting,
  showToast,
}) => {
  const workspaceId = activeWorkspace?.id || null;
  const { data: documents, mutate: mutateDocs, isLoading: docsLoading } = useWorkspaceDocuments(
    workspaceId,
    getToken
  );

  const [chatMessages, setChatMessages] = useState<ApiKnowledgeChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Hello! I am your MeetPilot Workspace Knowledge Assistant. I have grounded access to your uploaded company documents and meeting transcripts. Ask me anything about your product roadmap, engineering specs, policies, or past meeting discussions!',
      time: 'Just now',
    },
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [selectedDocForPreview, setSelectedDocForPreview] = useState<ApiKnowledgeCitation | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isSending]);

  // Suggested prompt starters
  const suggestedPrompts = [
    'What are our core product priorities?',
    'Summarize recent engineering decisions.',
    'Compare our roadmap with latest meeting discussions.',
    'What does our company documentation say about remote policies?',
  ];

  const handleSendMessage = async (textToSend?: string) => {
    const question = (textToSend || chatInput).trim();
    if (!question || !workspaceId || isSending) return;

    const userMsg: ApiKnowledgeChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setChatMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setChatInput('');
    setIsSending(true);

    try {
      const response = await sendKnowledgeChatApi(workspaceId, question, getToken);
      const aiMsg: ApiKnowledgeChatMessage = {
        id: `ai-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        citations: response.citations,
      };
      setChatMessages((prev) => [...prev, aiMsg]);
    } catch (err: any) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `Error retrieving workspace knowledge: ${err.message || 'Server error'}`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !workspaceId) return;

    setIsUploading(true);
    let successCount = 0;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setUploadProgress(`Processing ${file.name} (${i + 1}/${files.length})...`);
      try {
        await uploadDocumentApi(workspaceId, file, getToken);
        successCount++;
      } catch (err: any) {
        showToast(`Failed to upload ${file.name}: ${err.message}`, 'error');
      }
    }

    await mutateDocs();
    setIsUploading(false);
    setUploadProgress(null);
    if (fileInputRef.current) fileInputRef.current.value = '';

    if (successCount > 0) {
      showToast(`Successfully indexed ${successCount} document(s) into workspace knowledge base.`, 'success');
    }
  };

  const handleDeleteDocument = async (doc: ApiKnowledgeDocument) => {
    if (!confirm(`Are you sure you want to delete '${doc.filename}' and all its indexed chunks?`)) return;

    try {
      await deleteDocumentApi(doc.id, getToken);
      await mutateDocs();
      showToast(`Deleted ${doc.filename}`, 'info');
    } catch (err: any) {
      showToast(`Failed to delete document: ${err.message}`, 'error');
    }
  };

  const parseTimestampToSeconds = (ts?: string | null): number | undefined => {
    if (!ts) return undefined;
    const parts = ts.split(':').map(Number);
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    return undefined;
  };

  const getFileIcon = (fileType: string) => {
    switch (fileType.toLowerCase()) {
      case 'pdf':
        return <FileText className="w-5 h-5 text-rose-400 shrink-0" />;
      case 'docx':
      case 'doc':
        return <FileText className="w-5 h-5 text-sky-400 shrink-0" />;
      case 'md':
      case 'markdown':
        return <FileCode className="w-5 h-5 text-emerald-400 shrink-0" />;
      default:
        return <BookOpen className="w-5 h-5 text-purple-400 shrink-0" />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="flex-1 flex flex-col lg:flex-row overflow-hidden bg-[#0A0A0B]">
      {/* LEFT AREA: AI Knowledge Assistant Chat */}
      <div className="flex-1 flex flex-col border-r border-[#27272A] min-w-0 h-full">
        {/* Chat Header */}
        <div className="p-4 border-b border-[#27272A] bg-[#111113]/80 backdrop-blur flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#8B5CF6]/30 to-[#3B82F6]/20 border border-[#8B5CF6]/30 flex items-center justify-center">
              <Brain className="w-5 h-5 text-[#8B5CF6]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold text-white">Workspace AI Assistant</h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  RAG Active
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Grounded on {documents?.length || 0} company document(s) & workspace meeting transcripts
              </p>
            </div>
          </div>

          <button
            onClick={() =>
              setChatMessages([
                {
                  id: 'reset',
                  role: 'assistant',
                  content: 'Conversation cleared. How can I assist you with your workspace knowledge today?',
                  time: 'Just now',
                },
              ])
            }
            title="Clear Chat History"
            className="p-2 rounded-lg bg-[#18181b] hover:bg-[#27272A] text-slate-400 hover:text-white text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">New Chat</span>
          </button>
        </div>

        {/* Chat Messages Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {chatMessages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-xl bg-[#8B5CF6]/20 border border-[#8B5CF6]/40 flex items-center justify-center shrink-0 mt-0.5">
                  <Sparkles className="w-4 h-4 text-[#8B5CF6]" />
                </div>
              )}

              <div
                className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 text-xs leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-[#8B5CF6] text-white font-medium rounded-tr-sm shadow-md shadow-[#8B5CF6]/20'
                    : 'bg-[#18181b] border border-[#27272A] text-slate-200 rounded-tl-sm'
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>

                {/* Grounded Source Citations */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-[#27272A] space-y-2">
                    <div className="text-[10px] font-mono uppercase text-[#8B5CF6] font-bold flex items-center gap-1">
                      <Layers className="w-3 h-3" /> Grounded Source Citations ({msg.citations.length})
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {msg.citations.map((cite, idx) => (
                        <div
                          key={idx}
                          onClick={() => {
                            if (cite.type === 'meeting' && cite.meeting_id && onNavigateToMeeting) {
                              onNavigateToMeeting(cite.meeting_id, parseTimestampToSeconds(cite.timestamp));
                            } else {
                              setSelectedDocForPreview(cite);
                            }
                          }}
                          className="group px-2.5 py-1.5 rounded-lg bg-[#27272A]/70 hover:bg-[#8B5CF6]/20 border border-[#3f3f46] hover:border-[#8B5CF6]/50 text-[11px] text-slate-300 hover:text-white flex items-center gap-1.5 cursor-pointer transition-all"
                        >
                          {cite.type === 'meeting' ? (
                            <>
                              <Mic className="w-3 h-3 text-rose-400 shrink-0" />
                              <span className="font-semibold text-rose-300">🎙️ {cite.title}</span>
                              {cite.timestamp && (
                                <span className="font-mono text-[10px] text-slate-400 group-hover:text-white">
                                  @{cite.timestamp}
                                </span>
                              )}
                              <ExternalLink className="w-2.5 h-2.5 opacity-60 group-hover:opacity-100" />
                            </>
                          ) : (
                            <>
                              <FileText className="w-3 h-3 text-sky-400 shrink-0" />
                              <span className="font-semibold text-sky-300">📄 {cite.title}</span>
                              {cite.page_number && (
                                <span className="font-mono text-[10px] text-slate-400 group-hover:text-white">
                                  (p. {cite.page_number})
                                </span>
                              )}
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-2 text-[10px] opacity-60 text-right">{msg.time}</div>
              </div>
            </div>
          ))}

          {isSending && (
            <div className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-xl bg-[#8B5CF6]/20 border border-[#8B5CF6]/40 flex items-center justify-center shrink-0 animate-pulse">
                <Sparkles className="w-4 h-4 text-[#8B5CF6]" />
              </div>
              <div className="p-3.5 rounded-2xl bg-[#18181b] border border-[#27272A] text-xs text-slate-400 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[#8B5CF6] animate-ping" />
                Searching pgvector workspace embeddings & synthesizing grounded response...
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Suggested Starter Prompts */}
        {chatMessages.length <= 1 && (
          <div className="px-4 pb-2">
            <div className="text-[11px] font-mono text-slate-500 mb-2 uppercase">Suggested Inquiries</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {suggestedPrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(prompt)}
                  className="p-2.5 rounded-xl bg-[#18181b] hover:bg-[#27272A] border border-[#27272A] hover:border-[#8B5CF6]/40 text-left text-xs text-slate-300 hover:text-white transition-all cursor-pointer flex items-center justify-between"
                >
                  <span className="truncate pr-2">{prompt}</span>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Chat Input Bar */}
        <div className="p-4 border-t border-[#27272A] bg-[#111113]/80">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask anything about your workspace documents or meeting discussions..."
              disabled={isSending}
              className="flex-1 px-4 py-3 rounded-xl bg-[#18181b] border border-[#27272A] text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#8B5CF6] transition-colors"
            />
            <button
              type="submit"
              disabled={isSending || !chatInput.trim()}
              className="px-4 py-3 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] disabled:opacity-50 text-white text-xs font-bold flex items-center gap-2 transition-all cursor-pointer shadow-lg shadow-[#8B5CF6]/20 shrink-0"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Ask AI</span>
            </button>
          </form>
        </div>
      </div>

      {/* RIGHT AREA: Workspace Document Knowledge Base Manager */}
      <div className="w-full lg:w-96 flex flex-col bg-[#111113] h-full">
        {/* Knowledge Base Header */}
        <div className="p-4 border-b border-[#27272A] flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-[#8B5CF6]" />
              <h2 className="text-sm font-bold text-white">Company Knowledge</h2>
            </div>
            <p className="text-[11px] text-slate-400">PDF, DOCX, TXT, Markdown files</p>
          </div>

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="px-3 py-1.5 rounded-lg bg-[#8B5CF6] hover:bg-[#7c3aed] text-white text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-md shadow-[#8B5CF6]/20"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Upload</span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.md,.markdown"
            onChange={handleFileUpload}
            className="hidden"
          />
        </div>

        {/* Upload Progress Alert */}
        {uploadProgress && (
          <div className="p-3 bg-[#8B5CF6]/10 border-b border-[#8B5CF6]/30 text-xs text-[#8B5CF6] flex items-center gap-2">
            <RefreshCw className="w-3.5 h-3.5 animate-spin shrink-0" />
            <span className="truncate">{uploadProgress}</span>
          </div>
        )}

        {/* Document List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {docsLoading ? (
            <div className="text-center py-8 text-xs text-slate-500">Loading workspace documents...</div>
          ) : !documents || documents.length === 0 ? (
            <div className="text-center py-12 px-4 border border-dashed border-[#27272A] rounded-2xl">
              <div className="w-12 h-12 rounded-2xl bg-[#18181b] border border-[#27272A] flex items-center justify-center mx-auto mb-3">
                <Upload className="w-6 h-6 text-slate-500" />
              </div>
              <h3 className="text-xs font-bold text-white mb-1">Your workspace knowledge base is empty</h3>
              <p className="text-[11px] text-slate-400 mb-4 max-w-xs mx-auto">
                Upload company documents, product roadmaps, policies, or specifications to empower your AI assistant with workspace memory.
              </p>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-3.5 py-2 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] text-white text-xs font-bold inline-flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                Upload Documents
              </button>
            </div>
          ) : (
            documents.map((doc) => (
              <div
                key={doc.id}
                className="p-3 rounded-xl bg-[#18181b] border border-[#27272A] hover:border-[#3f3f46] transition-all group"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2.5 min-w-0">
                    {getFileIcon(doc.file_type)}
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-white truncate group-hover:text-[#8B5CF6] transition-colors">
                        {doc.title || doc.filename}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono flex items-center gap-2 mt-0.5">
                        <span>{doc.file_type.toUpperCase()}</span>
                        <span>•</span>
                        <span>{formatFileSize(doc.file_size)}</span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDeleteDocument(doc)}
                    title="Delete document"
                    className="p-1 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors opacity-60 group-hover:opacity-100 cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Status & Chunks Strip */}
                <div className="mt-2.5 pt-2 border-t border-[#27272A] flex items-center justify-between text-[10px]">
                  <div className="flex items-center gap-1.5">
                    {doc.status === 'ready' && (
                      <span className="flex items-center gap-1 text-emerald-400 font-medium">
                        <CheckCircle2 className="w-3 h-3" /> Indexed
                      </span>
                    )}
                    {doc.status === 'processing' && (
                      <span className="flex items-center gap-1 text-amber-400 font-medium animate-pulse">
                        <RefreshCw className="w-3 h-3 animate-spin" /> Indexing
                      </span>
                    )}
                    {doc.status === 'failed' && (
                      <span className="flex items-center gap-1 text-rose-400 font-medium" title={doc.failure_reason || ''}>
                        <AlertCircle className="w-3 h-3" /> Failed
                      </span>
                    )}
                  </div>

                  <div className="font-mono text-slate-400">
                    <span className="text-white font-bold">{doc.chunk_count}</span> vector chunks
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Snippet Preview Modal */}
      {selectedDocForPreview && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-2xl bg-[#18181b] border border-[#27272A] p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#27272A] pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-sky-400" />
                <h3 className="text-xs font-bold text-white">{selectedDocForPreview.title}</h3>
                {selectedDocForPreview.page_number && (
                  <span className="text-[10px] font-mono text-slate-400">
                    (Page {selectedDocForPreview.page_number})
                  </span>
                )}
              </div>
              <button
                onClick={() => setSelectedDocForPreview(null)}
                className="text-slate-400 hover:text-white text-xs cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div>
              <div className="text-[10px] font-mono uppercase text-slate-500 mb-1">Retrieved Context Snippet</div>
              <div className="p-3 rounded-xl bg-[#111113] border border-[#27272A] text-xs text-slate-300 font-mono leading-relaxed whitespace-pre-wrap max-h-60 overflow-y-auto">
                {selectedDocForPreview.snippet}
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setSelectedDocForPreview(null)}
                className="px-4 py-2 rounded-xl bg-[#27272A] hover:bg-[#3f3f46] text-white text-xs font-bold cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
