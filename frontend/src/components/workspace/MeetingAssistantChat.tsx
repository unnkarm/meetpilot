import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Send,
  Loader2,
  Bot,
  User,
  Play,
  HelpCircle,
} from 'lucide-react';

export interface ChatMessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  cited_timestamp?: string | null;
  time?: string;
}

interface MeetingAssistantChatProps {
  meetingTitle: string;
  messages: ChatMessageItem[];
  isSending: boolean;
  onSendMessage: (message: string) => Promise<void>;
  onSeek: (seconds: number) => void;
}

const SUGGESTED_QUESTIONS = [
  'What were the key decisions agreed in this meeting?',
  'What action items were assigned and to whom?',
  'Summarize the meeting in 3 concise bullet points.',
  'What technical architecture deliverables were discussed?',
];

export const MeetingAssistantChat: React.FC<MeetingAssistantChatProps> = ({
  meetingTitle,
  messages,
  isSending,
  onSendMessage,
  onSeek,
}) => {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const parseTimestampSeconds = (ts?: string | null): number | null => {
    if (!ts) return null;
    const parts = ts.replace('@', '').split(':').map(Number);
    if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
      return parts[0] * 60 + parts[1];
    }
    const single = Number(ts);
    return !isNaN(single) ? single : null;
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isSending) return;
    const text = inputValue.trim();
    setInputValue('');
    await onSendMessage(text);
  };

  const handleSuggestionClick = async (suggestion: string) => {
    if (isSending) return;
    await onSendMessage(suggestion);
  };

  return (
    <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4 shadow-xl flex flex-col h-[600px]">
      {/* Header with Title + RAG Grounding Indicator */}
      <div className="flex items-center justify-between pb-3 border-b border-[#27272A]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-[#8B5CF6]/15 border border-[#8B5CF6]/30 flex items-center justify-center text-[#8B5CF6]">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Meeting AI Assistant
            </h3>
            <p className="text-[11px] text-slate-400">
              Grounded in audio transcript & pgvector embeddings
            </p>
          </div>
        </div>

        <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
          ● RAG Indexed
        </span>
      </div>

      {/* Suggested Questions Chips (shown if low message count) */}
      {messages.length <= 2 && (
        <div className="space-y-2 pb-2">
          <div className="flex items-center gap-1 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
            <HelpCircle className="w-3 h-3 text-[#8B5CF6]" />
            <span>Suggested Inquiries</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {SUGGESTED_QUESTIONS.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestionClick(q)}
                disabled={isSending}
                className="text-left p-2.5 rounded-xl bg-[#18181b] border border-[#27272A] hover:border-[#8B5CF6]/50 text-xs text-slate-300 hover:text-white transition-all cursor-pointer shadow-sm"
              >
                "{q}"
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages Thread Container */}
      <div className="flex-1 overflow-y-auto space-y-3.5 pr-2 scrollbar-thin">
        {messages.length === 0 && (
          <div className="p-8 text-center border border-dashed border-[#27272A] rounded-xl space-y-2 my-auto">
            <Bot className="w-8 h-8 text-[#8B5CF6] mx-auto" />
            <p className="text-xs text-slate-300 font-semibold">
              Ask anything about "{meetingTitle}"
            </p>
            <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
              MeetPilot AI answers with timestamped source citations verified directly from the speech recording.
            </p>
          </div>
        )}

        {messages.map((msg, idx) => {
          const isUser = msg.role === 'user';
          const seekSecs = parseTimestampSeconds(msg.cited_timestamp);

          return (
            <div
              key={msg.id || idx}
              className={`flex items-start gap-2.5 ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              {!isUser && (
                <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-[#8B5CF6] to-indigo-600 flex items-center justify-center text-white shrink-0 shadow-sm mt-1">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`p-4 rounded-2xl max-w-xl text-xs sm:text-sm leading-relaxed space-y-2 shadow-sm ${
                  isUser
                    ? 'bg-[#8B5CF6] text-white rounded-br-none'
                    : 'bg-[#18181b] border border-[#27272A] text-slate-200 rounded-bl-none'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>

                {msg.cited_timestamp && seekSecs !== null && (
                  <div className="pt-1.5 border-t border-white/10">
                    <button
                      onClick={() => onSeek(seekSecs)}
                      className="text-[11px] font-mono text-cyan-300 hover:text-white bg-cyan-950/60 border border-cyan-500/30 px-2 py-0.5 rounded-lg flex items-center gap-1 cursor-pointer transition-colors"
                    >
                      <Play className="w-2.5 h-2.5 fill-current" />
                      <span>Source audio citation: @{msg.cited_timestamp.replace('@', '')} (Click to listen)</span>
                    </button>
                  </div>
                )}
              </div>

              {isUser && (
                <div className="w-7 h-7 rounded-lg bg-[#27272A] flex items-center justify-center text-slate-300 shrink-0 shadow-sm mt-1">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}

        {isSending && (
          <div className="flex items-center gap-2.5 text-xs text-slate-400 p-3 bg-[#18181b] rounded-xl border border-[#27272A] w-fit">
            <Loader2 className="w-4 h-4 animate-spin text-[#8B5CF6]" />
            <span>Retrieving relevant speech context and synthesizing answer...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Field & Submit */}
      <form onSubmit={handleSubmit} className="flex items-center gap-2 pt-2 border-t border-[#27272A]">
        <input
          type="text"
          placeholder="Ask a question about this meeting..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          className="flex-1 bg-[#18181b] border border-[#27272A] rounded-xl px-4 py-2.5 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#8B5CF6]"
        />

        <button
          type="submit"
          disabled={!inputValue.trim() || isSending}
          className="px-4 py-2.5 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] disabled:opacity-40 text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-lg shadow-[#8B5CF6]/20 transition-all shrink-0"
        >
          <Send className="w-3.5 h-3.5" />
          <span>Ask</span>
        </button>
      </form>
    </div>
  );
};
