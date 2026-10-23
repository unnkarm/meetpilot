import React, { useState, useRef, useEffect } from 'react';
import { useMeetingText } from './MeetingLanguageDisplay';
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
  const displayText = useMeetingText();
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
    <div className="p-6 rounded-xl bg-surface border border-line space-y-4 shadow-sm flex flex-col h-[600px]">
      {/* Header with Title + RAG Grounding Indicator */}
      <div className="flex items-center justify-between pb-3 border-b border-line">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-brand/15 border border-brand/30 flex items-center justify-center text-brand">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-ink uppercase tracking-wider">
              Meeting AI Assistant
            </h3>
            <p className="text-sm text-muted">
              Answers based on this meeting, with source timestamps
            </p>
          </div>
        </div>

        <span className="text-sm font-mono font-bold text-emerald-700 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
          ● RAG Indexed
        </span>
      </div>

      {/* Suggested Questions Chips (shown if low message count) */}
      {messages.length <= 2 && (
        <div className="space-y-2 pb-2">
          <div className="flex items-center gap-1 text-sm font-mono text-muted uppercase tracking-wider">
            <HelpCircle className="w-3 h-3 text-brand" />
            <span>Suggested Inquiries</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {SUGGESTED_QUESTIONS.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestionClick(q)}
                disabled={isSending}
                className="text-left p-2.5 rounded-xl bg-surface border border-line hover:border-brand/50 text-sm text-ink hover:text-ink transition-all cursor-pointer shadow-sm"
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
          <div className="p-8 text-center border border-dashed border-line rounded-xl space-y-2 my-auto">
            <Bot className="w-8 h-8 text-brand mx-auto" />
            <p className="text-sm text-ink font-semibold">
              Ask anything about "{meetingTitle}"
            </p>
            <p className="text-sm text-muted max-w-sm mx-auto">
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
                <div className="w-7 h-7 rounded-lg bg-brand-soft flex items-center justify-center text-ink shrink-0 shadow-sm mt-1">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`p-4 rounded-xl max-w-xl text-sm sm:text-sm leading-relaxed space-y-2 shadow-sm ${
                  isUser
                    ? 'bg-brand text-on-brand rounded-br-none'
                    : 'bg-surface border border-line text-ink rounded-bl-none'
                }`}
              >
                <p className="whitespace-pre-wrap">{displayText(msg.content)}</p>

                {msg.cited_timestamp && seekSecs !== null && (
                  <div className="pt-1.5 border-t border-line">
                    <button
                      onClick={() => onSeek(seekSecs)}
                      className="text-sm font-mono text-cyan-700 hover:text-ink bg-cyan-50 border border-cyan-500/30 px-2 py-0.5 rounded-lg flex items-center gap-1 cursor-pointer transition-colors"
                    >
                      <Play className="w-2.5 h-2.5 fill-current" />
                      <span>Source audio citation: @{msg.cited_timestamp.replace('@', '')} (Click to listen)</span>
                    </button>
                  </div>
                )}
              </div>

              {isUser && (
                <div className="w-7 h-7 rounded-lg bg-line flex items-center justify-center text-ink shrink-0 shadow-sm mt-1">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}

        {isSending && (
          <div className="flex items-center gap-2.5 text-sm text-muted p-3 bg-surface rounded-xl border border-line w-fit">
            <Loader2 className="w-4 h-4 animate-spin text-brand" />
            <span>Retrieving relevant speech context and synthesizing answer...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Field & Submit */}
      <form onSubmit={handleSubmit} className="flex items-center gap-2 pt-2 border-t border-line">
        <input
          type="text"
          placeholder="Ask a question about this meeting..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          className="flex-1 bg-surface border border-line rounded-xl px-4 py-2.5 text-sm sm:text-sm text-ink placeholder-slate-500 focus:outline-none focus:border-brand"
        />

        <button
          type="submit"
          disabled={!inputValue.trim() || isSending}
          className="px-4 py-2.5 rounded-xl bg-brand hover:bg-brand disabled:opacity-40 text-on-brand text-sm font-bold flex items-center gap-1.5 cursor-pointer shadow-sm  transition-all shrink-0"
        >
          <Send className="w-3.5 h-3.5" />
          <span>Ask</span>
        </button>
      </form>
    </div>
  );
};
