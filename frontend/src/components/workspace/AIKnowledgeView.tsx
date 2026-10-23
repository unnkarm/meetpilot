import { Modal } from '../Modal';
import React, { useState, useRef, useEffect } from 'react';
import { useWorkspaceManager } from '../../utils/workspacePermissions';
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
  const canManage = useWorkspaceManager();
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
        'Ask a question about your team’s documents or past meetings. I’ll include sources when the workspace has supporting evidence.',
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
    if (!canManage) return;
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
    if (!canManage) return;
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
        return <FileText className="w-5 h-5 text-rose-700 shrink-0" />;
      case 'docx':
      case 'doc':
        return <FileText className="w-5 h-5 text-sky-700 shrink-0" />;
      case 'md':
      case 'markdown':
        return <FileCode className="w-5 h-5 text-emerald-700 shrink-0" />;
      default:
        return <BookOpen className="w-5 h-5 text-brand shrink-0" />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="mp-knowledge-layout flex flex-col lg:flex-row overflow-hidden">
      {/* LEFT AREA: AI Knowledge Assistant Chat */}
      <div className="flex-1 flex flex-col border-r border-line min-w-0 h-full">
        {/* Chat Header */}
        <div className="p-4 border-b border-line bg-surface/80 backdrop-blur flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-brand-soft border border-brand/30 flex items-center justify-center">
              <Brain className="w-5 h-5 text-brand" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold text-ink">Ask your workspace</h1>
                <span className="px-2 py-0.5 rounded-full text-sm font-mono bg-emerald-500/10 text-emerald-700 border border-emerald-500/20">
                  With sources
                </span>
              </div>
              <p className="text-sm text-muted">
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
            className="p-2 rounded-lg bg-surface hover:bg-line text-muted hover:text-ink text-sm flex items-center gap-1.5 transition-colors cursor-pointer"
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
                <div className="w-8 h-8 rounded-xl bg-brand/20 border border-brand/40 flex items-center justify-center shrink-0 mt-0.5">
                  <Sparkles className="w-4 h-4 text-brand" />
                </div>
              )}

              <div
                className={`max-w-[85%] sm:max-w-[75%] rounded-xl p-4 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-brand text-on-brand font-medium rounded-tr-sm shadow-md '
                    : 'bg-surface border border-line text-ink rounded-tl-sm'
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>

                {/* Sources */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-line space-y-2">
                    <div className="text-sm font-mono uppercase text-brand font-bold flex items-center gap-1">
                      <Layers className="w-3 h-3" /> Sources ({msg.citations.length})
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {msg.citations.map((cite, idx) => (
                        <button type="button"
                          key={idx}
                          onClick={() => {
                            if (cite.meeting_id && onNavigateToMeeting) {
                              onNavigateToMeeting(cite.meeting_id, parseTimestampToSeconds(cite.timestamp));
                            } else {
                              setSelectedDocForPreview(cite);
                            }
                          }}
                          className="group px-2.5 py-1.5 rounded-lg bg-line/70 hover:bg-brand/20 border border-line hover:border-brand/50 text-sm text-ink hover:text-ink flex items-center gap-1.5 cursor-pointer transition-all"
                        >
                          {cite.meeting_id ? (
                            <>
                              <Mic className="w-3 h-3 text-rose-700 shrink-0" />
                              <span className="font-semibold text-brand">{cite.title}</span>
                              {cite.timestamp && (
                                <span className="font-mono text-sm text-muted group-hover:text-ink">
                                  @{cite.timestamp}
                                </span>
                              )}
                              <ExternalLink className="w-2.5 h-2.5 opacity-60 group-hover:opacity-100" />
                            </>
                          ) : (
                            <>
                              <FileText className="w-3 h-3 text-sky-700 shrink-0" />
                              <span className="font-semibold text-sky-700">{cite.title}</span>
                              {cite.page_number && (
                                <span className="font-mono text-sm text-muted group-hover:text-ink">
                                  (p. {cite.page_number})
                                </span>
                              )}
                            </>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-2 text-sm opacity-60 text-right">{msg.time}</div>
              </div>
            </div>
          ))}

          {isSending && (
            <div className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-xl bg-brand/20 border border-brand/40 flex items-center justify-center shrink-0 animate-pulse">
                <Sparkles className="w-4 h-4 text-brand" />
              </div>
              <div className="p-3.5 rounded-xl bg-surface border border-line text-sm text-muted flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-brand " />
                Searching pgvector workspace embeddings & synthesizing grounded response...
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Suggested Starter Prompts */}
        {chatMessages.length <= 1 && (
          <div className="px-4 pb-2">
            <div className="text-sm font-mono text-muted mb-2 uppercase">Suggested Inquiries</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {suggestedPrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(prompt)}
                  className="p-2.5 rounded-xl bg-surface hover:bg-line border border-line hover:border-brand/40 text-left text-sm text-ink hover:text-ink transition-all cursor-pointer flex items-center justify-between"
                >
                  <span className="truncate pr-2">{prompt}</span>
                  <ChevronRight className="w-3.5 h-3.5 text-muted shrink-0" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Chat Input Bar */}
        <div className="p-4 border-t border-line bg-surface/80">
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
              aria-label="Ask workspace knowledge" placeholder="Ask anything about your workspace documents or meeting discussions..."
              disabled={isSending}
              className="flex-1 px-4 py-3 rounded-xl bg-surface border border-line text-sm text-ink placeholder-slate-500 focus:outline-none focus:border-brand transition-colors"
            />
            <button
              type="submit"
              disabled={isSending || !chatInput.trim()}
              className="px-4 py-3 rounded-xl bg-brand hover:bg-brand disabled:opacity-50 text-on-brand text-sm font-bold flex items-center gap-2 transition-all cursor-pointer shadow-sm  shrink-0"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Ask AI</span>
            </button>
          </form>
        </div>
      </div>

      {/* RIGHT AREA: Workspace Document Knowledge Base Manager */}
      <div className="w-full lg:w-96 flex flex-col bg-surface h-full">
        {/* Knowledge Base Header */}
        <div className="p-4 border-b border-line flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-brand" />
              <h2 className="text-sm font-bold text-ink">Documents</h2>
            </div>
            <p className="text-sm text-muted">{canManage ? 'PDF, DOCX, TXT, Markdown files' : 'Use shared knowledge · documents are managed by your manager'}</p>
          </div>

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading || !canManage} aria-label="Upload knowledge documents"
            className="px-3 py-1.5 rounded-lg bg-brand hover:bg-brand text-on-brand text-sm font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-md "
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
          <div className="p-3 bg-brand/10 border-b border-brand/30 text-sm text-brand flex items-center gap-2">
            <RefreshCw className="w-3.5 h-3.5 animate-spin shrink-0" />
            <span className="truncate">{uploadProgress}</span>
          </div>
        )}

        {/* Document List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {docsLoading ? (
            <div className="text-center py-8 text-sm text-muted">Loading workspace documents...</div>
          ) : !documents || documents.length === 0 ? (
            <div className="text-center py-12 px-4 border border-dashed border-line rounded-xl">
              <div className="w-12 h-12 rounded-xl bg-surface border border-line flex items-center justify-center mx-auto mb-3">
                <Upload className="w-6 h-6 text-muted" />
              </div>
              <h3 className="text-sm font-bold text-ink mb-1">Your workspace knowledge base is empty</h3>
              <p className="text-sm text-muted mb-4 max-w-xs mx-auto">
                Upload company documents, product roadmaps, policies, or specifications to empower your AI assistant with workspace memory.
              </p>
              <button
                disabled={!canManage}
                onClick={() => fileInputRef.current?.click()}
                className="px-3.5 py-2 rounded-xl bg-brand hover:bg-brand text-on-brand text-sm font-bold inline-flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                Upload Documents
              </button>
            </div>
          ) : (
            documents.map((doc) => (
              <div
                key={doc.id}
                className="p-3 rounded-xl bg-surface border border-line hover:border-line transition-all group"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2.5 min-w-0">
                    {getFileIcon(doc.file_type)}
                    <div className="min-w-0">
                      <div className="text-sm font-bold text-ink truncate group-hover:text-brand transition-colors">
                        {doc.title || doc.filename}
                      </div>
                      <div className="text-sm text-muted font-mono flex items-center gap-2 mt-0.5">
                        <span>{doc.file_type.toUpperCase()}</span>
                        <span>•</span>
                        <span>{formatFileSize(doc.file_size)}</span>
                      </div>
                    </div>
                  </div>

                  <button
                    disabled={!canManage}
                    onClick={() => handleDeleteDocument(doc)}
                    title="Delete document"
                    className="p-1 rounded-lg text-muted hover:text-rose-700 hover:bg-rose-500/10 transition-colors opacity-60 group-hover:opacity-100 cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Status & Chunks Strip */}
                <div className="mt-2.5 pt-2 border-t border-line flex items-center justify-between text-sm">
                  <div className="flex items-center gap-1.5">
                    {doc.status === 'ready' && (
                      <span className="flex items-center gap-1 text-emerald-700 font-medium">
                        <CheckCircle2 className="w-3 h-3" /> Indexed
                      </span>
                    )}
                    {doc.status === 'processing' && (
                      <span className="flex items-center gap-1 text-amber-700 font-medium animate-pulse">
                        <RefreshCw className="w-3 h-3 animate-spin" /> Indexing
                      </span>
                    )}
                    {doc.status === 'failed' && (
                      <span className="flex items-center gap-1 text-rose-700 font-medium" title={doc.failure_reason || ''}>
                        <AlertCircle className="w-3 h-3" /> Failed
                      </span>
                    )}
                  </div>

                  <div className="font-mono text-muted">
                    <span className="text-ink font-bold">{doc.chunk_count}</span> vector chunks
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Snippet Preview Modal */}
      {selectedDocForPreview && (
        <Modal label="Knowledge source" onClose={() => setSelectedDocForPreview(null)}>
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-sky-700" />
                <h3 className="text-sm font-bold text-ink">{selectedDocForPreview.title}</h3>
                {selectedDocForPreview.page_number && (
                  <span className="text-sm font-mono text-muted">
                    (Page {selectedDocForPreview.page_number})
                  </span>
                )}
              </div>
              <button
                onClick={() => setSelectedDocForPreview(null)}
                className="text-muted hover:text-ink text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div>
              <div className="text-sm font-mono uppercase text-muted mb-1">Retrieved Context Snippet</div>
              <div className="p-3 rounded-xl bg-surface border border-line text-sm text-ink font-mono leading-relaxed whitespace-pre-wrap max-h-60 overflow-y-auto">
                {selectedDocForPreview.snippet}
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setSelectedDocForPreview(null)}
                className="px-4 py-2 rounded-xl bg-line hover:bg-line text-ink text-sm font-bold cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
