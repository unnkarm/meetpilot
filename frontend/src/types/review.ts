export interface ReviewCitation { source_segment_id: string; speaker: string; start_time: number; end_time: number; quote: string }
export interface ReviewPoint { text: string; source_ids: string[] }
export interface ReviewChapter { title: string; start_time: number; end_time: number; points: ReviewPoint[] }
export interface ReviewPayload {
  sections: { title: string; points: ReviewPoint[] }[];
  paragraphs: ReviewPoint[];
  chapters: ReviewChapter[];
  citations: Record<string, ReviewCitation>;
  subject?: string;
  coverage: { segments: number; windows: number; complete: boolean };
}
export interface ReviewArtifact {
  id: string; kind: 'summary' | 'followup' | 'chapters'; status: 'queued' | 'processing' | 'completed' | 'failed';
  options: { template_name?: string; audience?: string; format?: string };
  failure_reason?: string; ai_model?: string; stale?: boolean;
  payload?: ReviewPayload | null; progress?: { completed: number; total: number };
}
export interface SummaryTemplate { id: string; name: string; instructions: string; builtin: boolean }
export interface MeetingBookmark { id: string; kind: string; label: string; position_seconds: number; can_delete: boolean }
export interface ReviewRisk {
  id: string; kind: string; title: string; reasons: string[]; source_segment_id?: string;
  quote?: string; speaker?: string; timestamp?: string; position_seconds?: number;
}
export interface ReviewMetrics {
  duration_seconds: number; speech_seconds: number; silence_seconds: number; overlap_speaker_seconds: number;
  notes: string[];
  speakers: { speaker: string; speaking_seconds: number; words: number; questions: number; fillers: number;
    longest_monologue_seconds: number; monologues_over_90s: number; words_per_minute?: number; talk_share_percent: number }[];
}
