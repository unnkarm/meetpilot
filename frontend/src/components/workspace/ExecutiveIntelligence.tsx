import React, { useState } from 'react';
import {
  FileText,
  CheckCircle2,
  ChevronRight,
  Sparkles,
  ShieldCheck,
  Play,
  ArrowRight,
  Edit3,
  Trash2,
  Save,
  X,
} from 'lucide-react';
import { ApiMeetingSummary, ApiDecision } from '../../types';
import { formatTimeSeconds } from '../../utils/speakerUtils';
import { useMeetingText } from './MeetingLanguageDisplay';
import { useWorkspaceManager } from '../../utils/workspacePermissions';

interface ExecutiveIntelligenceProps {
  summary?: ApiMeetingSummary | null;
  decisions: ApiDecision[];
  onSeek: (seconds: number) => void;
  onEditSummary: (overview: string) => Promise<void>;
  onEditDecision: (id: string, topic: string, outcome: string) => Promise<void>;
  onDeleteDecision: (id: string) => Promise<void>;
}

export const ExecutiveIntelligence: React.FC<ExecutiveIntelligenceProps> = ({
  summary,
  decisions,
  onSeek,
  onEditSummary,
  onEditDecision,
  onDeleteDecision,
}) => {
  const canManage = useWorkspaceManager();
  const displayText = useMeetingText();
  const [editingSummary, setEditingSummary] = useState(false);
  const [summaryDraft, setSummaryDraft] = useState('');
  const [editingDecisionId, setEditingDecisionId] = useState<string | null>(null);
  const [topicDraft, setTopicDraft] = useState('');
  const [outcomeDraft, setOutcomeDraft] = useState('');
  const [saving, setSaving] = useState(false);

  const saveSummary = async () => {
    if (summaryDraft.trim().length < 3) return;
    setSaving(true);
    try {
      await onEditSummary(summaryDraft.trim());
      setEditingSummary(false);
    } finally { setSaving(false); }
  };

  const saveDecision = async () => {
    if (!editingDecisionId || topicDraft.trim().length < 3 || outcomeDraft.trim().length < 3) return;
    setSaving(true);
    try {
      await onEditDecision(editingDecisionId, topicDraft.trim(), outcomeDraft.trim());
      setEditingDecisionId(null);
    } finally { setSaving(false); }
  };
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
          <div className="p-6 rounded-xl bg-surface border border-line space-y-3.5 shadow-sm">
            <div className="flex items-center justify-between pb-2 border-b border-line">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-brand" />
                <h3 className="text-sm font-bold text-ink uppercase tracking-wider">
                  Executive Summary
                </h3>
              </div>
              <div className="flex items-center gap-1.5 text-sm font-mono text-emerald-700">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>AI draft</span>
                <button disabled={!canManage} type="button" onClick={() => { setSummaryDraft(summary?.overview || ''); setEditingSummary(true); }}
                  className="ml-2 text-ink hover:text-ink" aria-label="Edit summary"><Edit3 className="w-3.5 h-3.5" /></button>
              </div>
            </div>

            {editingSummary ? (
              <div className="space-y-2">
                <textarea value={summaryDraft} onChange={(event) => setSummaryDraft(event.target.value)}
                  className="w-full min-h-28 text-sm text-ink bg-surface p-3 rounded-xl border border-brand/50" aria-label="Summary text" />
                <div className="flex gap-2 justify-end">
                  <button type="button" onClick={() => setEditingSummary(false)} className="text-sm text-ink px-3 py-1">Cancel</button>
                  <button type="button" onClick={saveSummary} disabled={saving || summaryDraft.trim().length < 3}
                    className="text-sm text-on-brand bg-brand px-3 py-1 rounded disabled:opacity-50">Save</button>
                </div>
              </div>
            ) : (
              <p className="text-sm sm:text-sm text-ink leading-relaxed bg-surface p-4 rounded-xl border border-line font-normal">
                {displayText(summary?.overview) || 'Meeting synthesis is being prepared...'}
              </p>
            )}

            <div className="flex items-center gap-2 text-sm text-muted italic">
              <Sparkles className="w-3 h-3 text-brand" />
              <span>Grounded in speech transcript · Click timestamps to verify source audio.</span>
            </div>
          </div>

          {summary?.executive_sections && (
            <div className="p-6 rounded-xl bg-surface border border-line space-y-4">
              <h3 className="text-sm font-bold text-ink uppercase tracking-wider">Executive brief</h3>
              {([
                ['objectives', 'Objectives'], ['key_decisions', 'Key Decisions'],
                ['blockers', 'Blockers'], ['follow_ups', 'Follow-ups'],
              ] as const).map(([key, label]) => (
                <div key={key} className="space-y-2">
                  <h4 className="text-sm font-semibold text-brand">{label}</h4>
                  {(summary.executive_sections?.[key] || []).length === 0 ? (
                    <p className="text-sm text-muted">No verified {label.toLowerCase()} found.</p>
                  ) : summary.executive_sections?.[key]?.map((point, index) => (
                    <div key={`${key}:${index}`} className="rounded-lg bg-surface p-3 text-sm text-ink">
                      <p>{displayText(point.text)}</p>
                      <button type="button" className="mt-1 text-brand hover:underline"
                        onClick={() => { const seconds = parseTimestampSeconds(point.timestamp); if (seconds !== null) onSeek(seconds); }}>
                        {displayText(point.speaker)} · {point.timestamp}
                      </button>
                      <p className="mt-1 text-muted" title={point.source_quote}>“{displayText(point.source_quote)}”</p>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}

          {/* Key Takeaways */}
          <div className="p-6 rounded-xl bg-surface border border-line space-y-3.5 shadow-sm">
            <div className="flex items-center gap-2 pb-2 border-b border-line">
              <CheckCircle2 className="w-4 h-4 text-emerald-700" />
              <h3 className="text-sm font-bold text-ink uppercase tracking-wider">
                Key Takeaways
              </h3>
            </div>

            {summary?.key_takeaways && summary.key_takeaways.length > 0 ? (
              <div className="space-y-2.5">
                {summary.key_takeaways.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 text-sm sm:text-sm text-ink bg-surface p-3.5 rounded-xl border border-line hover:border-brand/30 transition-colors"
                  >
                    <span className="w-5 h-5 rounded-full bg-emerald-500/15 text-emerald-700 flex items-center justify-center shrink-0 mt-0.5 text-sm font-bold">
                      ✓
                    </span>
                    <span className="leading-relaxed">{displayText(item)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted italic p-4 bg-surface rounded-xl">
                No explicit key takeaways noted in this session.
              </p>
            )}
          </div>

          {/* Next Steps */}
          {summary?.next_steps && summary.next_steps.length > 0 && (
            <div className="p-6 rounded-xl bg-surface border border-line space-y-3.5 shadow-sm">
              <div className="flex items-center gap-2 pb-2 border-b border-line">
                <ArrowRight className="w-4 h-4 text-brand" />
                <h3 className="text-sm font-bold text-ink uppercase tracking-wider">
                  Next Steps
                </h3>
              </div>

              <div className="space-y-2.5">
                {summary.next_steps.map((step, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 text-sm sm:text-sm text-ink bg-surface p-3.5 rounded-xl border border-line hover:border-brand/30 transition-colors"
                  >
                    <ChevronRight className="w-4 h-4 text-brand shrink-0 mt-0.5" />
                    <span className="leading-relaxed">{displayText(step)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right (5 cols): Consensus Decisions Log */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-6 rounded-xl bg-surface border border-line space-y-4 shadow-sm">
            <div className="flex items-center justify-between pb-2 border-b border-line">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-700" />
                <h3 className="text-sm font-bold text-ink uppercase tracking-wider">
                  Consensus Decisions ({decisions.length})
                </h3>
              </div>
              <span className="text-sm font-mono text-muted">Agreed outcomes</span>
            </div>

            {decisions.length === 0 ? (
              <div className="p-8 text-center border border-dashed border-line rounded-xl space-y-2">
                <p className="text-sm text-muted">
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
                      className="p-4 rounded-xl bg-surface border border-line space-y-2 hover:border-amber-500/40 transition-colors shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-2">
                        {editingDecisionId === d.id ? (
                          <input value={topicDraft} onChange={(event) => setTopicDraft(event.target.value)}
                            className="text-sm text-ink bg-surface border border-amber-500/40 rounded p-1 flex-1 min-w-0" aria-label="Decision topic" />
                        ) : <span className="text-sm font-bold text-amber-700 leading-snug">{displayText(d.topic)}</span>}

                        {d.transcript_timestamp && seekSecs !== null && (
                          <button
                            onClick={() => onSeek(seekSecs)}
                            title="Jump audio to when this was decided"
                            className="text-sm font-mono text-amber-700 hover:text-ink bg-amber-500/10 hover:bg-amber-500 px-2 py-0.5 rounded-lg border border-amber-500/20 transition-colors cursor-pointer shrink-0 flex items-center gap-1 font-semibold"
                          >
                            <Play className="w-2.5 h-2.5 fill-current" />
                            <span>@{d.transcript_timestamp.replace('@', '')}</span>
                          </button>
                        )}
                      </div>

                      {editingDecisionId === d.id ? (
                        <div className="space-y-2">
                          <textarea value={outcomeDraft} onChange={(event) => setOutcomeDraft(event.target.value)}
                            className="text-sm text-ink bg-surface border border-amber-500/40 rounded p-2 w-full min-h-16" aria-label="Decision outcome" />
                          <div className="flex gap-2 justify-end">
                            <button type="button" onClick={() => setEditingDecisionId(null)} aria-label="Cancel editing decision"><X className="w-4 h-4 text-muted" /></button>
                            <button type="button" onClick={saveDecision} disabled={saving || topicDraft.trim().length < 3 || outcomeDraft.trim().length < 3}
                              aria-label="Save decision"><Save className="w-4 h-4 text-emerald-700" /></button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm text-ink leading-relaxed">{displayText(d.outcome)}</p>
                          <div className="flex gap-2 shrink-0">
                            <button disabled={!canManage} type="button" onClick={() => { setEditingDecisionId(d.id); setTopicDraft(d.topic); setOutcomeDraft(d.outcome); }}
                              className="text-muted hover:text-ink" aria-label={`Edit decision ${d.topic}`}><Edit3 className="w-3.5 h-3.5" /></button>
                            <button disabled={!canManage} type="button" onClick={() => onDeleteDecision(d.id)} className="text-muted hover:text-rose-700"
                              aria-label={`Remove decision ${d.topic}`}><Trash2 className="w-3.5 h-3.5" /></button>
                          </div>
                        </div>
                      )}
                      {(d.source_speaker || d.source_quote) && (
                        <p className="text-sm text-muted">
                          {d.source_speaker && <span>{displayText(d.source_speaker)}: </span>}
                          {d.source_quote && <span title={d.source_quote}>“{displayText(d.source_quote)}”</span>}
                        </p>
                      )}
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
