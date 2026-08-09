import React, { useState, useMemo, useRef, useEffect } from 'react';
import {
  Search,
  Users,
  Play,
  ArrowUp,
  ArrowDown,
  X,
  Volume2,
  FileText,
  Clock,
  Sparkles,
} from 'lucide-react';
import { ApiTranscriptSegment } from '../../types';
import {
  getSpeakerColorTheme,
  getSpeakerInitials,
  formatTimeSeconds,
  MeetingSpeakerStats,
} from '../../utils/speakerUtils';

interface DiarizedTranscriptProps {
  segments: ApiTranscriptSegment[];
  speakerStats: MeetingSpeakerStats;
  currentTime: number;
  onSeek: (seconds: number) => void;
  isLongRecording?: boolean;
}

export const DiarizedTranscript: React.FC<DiarizedTranscriptProps> = ({
  segments,
  speakerStats,
  currentTime,
  onSeek,
  isLongRecording,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [activeMatchIndex, setActiveMatchIndex] = useState(0);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const segmentRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Filter segments and identify search matches
  const { filteredSegments, searchMatchCount, matchingSegmentIds } = useMemo(() => {
    if (!searchQuery.trim()) {
      return {
        filteredSegments: segments,
        searchMatchCount: 0,
        matchingSegmentIds: [] as string[],
      };
    }

    const queryLower = searchQuery.toLowerCase();
    const matches: string[] = [];

    const filtered = segments.filter((seg) => {
      const match =
        seg.text.toLowerCase().includes(queryLower) ||
        seg.speaker.toLowerCase().includes(queryLower);
      if (match) matches.push(seg.id);
      return match;
    });

    return {
      filteredSegments: filtered,
      searchMatchCount: matches.length,
      matchingSegmentIds: matches,
    };
  }, [segments, searchQuery]);

  // Find currently active segment based on audio currentTime
  const activeSegmentId = useMemo(() => {
    const active = segments.find(
      (s) => currentTime >= s.start_time && currentTime <= s.end_time
    );
    return active ? active.id : null;
  }, [segments, currentTime]);

  // Auto-scroll active segment into view when autoScroll is enabled
  useEffect(() => {
    if (!autoScroll || !activeSegmentId) return;

    const el = segmentRefs.current.get(activeSegmentId);
    if (el && containerRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect();
      const elRect = el.getBoundingClientRect();

      // Only scroll if out of container's view
      if (elRect.top < containerRect.top || elRect.bottom > containerRect.bottom) {
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, [activeSegmentId, autoScroll]);

  // Navigate matching search results
  const scrollToMatch = (index: number) => {
    if (matchingSegmentIds.length === 0) return;
    const targetId = matchingSegmentIds[index];
    const el = segmentRefs.current.get(targetId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const handleNextMatch = () => {
    if (matchingSegmentIds.length === 0) return;
    const next = (activeMatchIndex + 1) % matchingSegmentIds.length;
    setActiveMatchIndex(next);
    scrollToMatch(next);
  };

  const handlePrevMatch = () => {
    if (matchingSegmentIds.length === 0) return;
    const prev = (activeMatchIndex - 1 + matchingSegmentIds.length) % matchingSegmentIds.length;
    setActiveMatchIndex(prev);
    scrollToMatch(prev);
  };

  const highlightText = (text: string, query: string) => {
    if (!query.trim()) return text;
    const parts = text.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
    return parts.map((part, i) =>
      part.toLowerCase() === query.toLowerCase() ? (
        <mark key={i} className="bg-amber-400/30 text-amber-200 px-0.5 rounded font-semibold">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4 shadow-xl">
      {/* Header & Controls Strip */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-3 border-b border-[#27272A]">
        {/* Left Side: Title & Speakers Badge */}
        <div className="space-y-1">
          <div className="flex items-center gap-2.5 flex-wrap">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <FileText className="w-4 h-4 text-[#8B5CF6]" />
              <span>Diarized Transcript</span>
              <span className="text-xs font-mono font-normal text-slate-400">
                ({segments.length} turns)
              </span>
            </h3>

            {isLongRecording && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#8B5CF6]/20 text-[#8B5CF6] border border-[#8B5CF6]/30">
                Speaker Continuity Active
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400">
            {speakerStats.displayLabel} · Click any timestamp or turn to jump playback.
          </p>
        </div>

        {/* Right Side: Search Input + Auto-Scroll Toggle */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Transcript Search Bar */}
          <div className="relative flex items-center">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 pointer-events-none" />
            <input
              type="text"
              placeholder="Search in transcript..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setActiveMatchIndex(0);
              }}
              className="bg-[#18181b] border border-[#27272A] rounded-xl pl-8 pr-8 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#8B5CF6] w-48 sm:w-56"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 text-slate-400 hover:text-white"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Search Result Counter & Nav */}
          {searchQuery && searchMatchCount > 0 && (
            <div className="flex items-center gap-1 bg-[#18181b] border border-[#27272A] px-2 py-1 rounded-xl text-xs font-mono">
              <span className="text-[#8B5CF6] font-bold">
                {activeMatchIndex + 1}/{searchMatchCount}
              </span>
              <button
                onClick={handlePrevMatch}
                title="Previous match"
                className="p-0.5 hover:text-white text-slate-400"
              >
                <ArrowUp className="w-3 h-3" />
              </button>
              <button
                onClick={handleNextMatch}
                title="Next match"
                className="p-0.5 hover:text-white text-slate-400"
              >
                <ArrowDown className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Auto-Scroll Toggle */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
              autoScroll
                ? 'bg-[#8B5CF6]/15 border-[#8B5CF6]/40 text-white'
                : 'bg-[#18181b] border-[#27272A] text-slate-400 hover:text-white'
            }`}
          >
            <Clock className="w-3 h-3 text-[#8B5CF6]" />
            <span>Follow Audio</span>
          </button>
        </div>
      </div>

      {/* Speaker Airtime Distribution Breakdown */}
      {speakerStats.airtime.length > 0 && (
        <div className="p-3.5 rounded-xl bg-[#18181b] border border-[#27272A] space-y-2">
          <div className="flex items-center justify-between text-[11px] font-mono font-semibold text-slate-400">
            <span className="flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-[#8B5CF6]" />
              <span>Participation Breakdown</span>
            </span>
            <span>{speakerStats.detectedCount} Speakers</span>
          </div>

          {/* Stacked Progress Bar */}
          <div className="h-2 w-full bg-[#111113] rounded-full overflow-hidden flex border border-[#27272A]">
            {speakerStats.airtime.map((spk, idx) => (
              <div
                key={idx}
                className={`h-full ${spk.colorTheme.avatarBg} transition-all duration-300`}
                style={{ width: `${spk.percentage}%` }}
                title={`${spk.speaker}: ${spk.percentage}% (${formatTimeSeconds(spk.durationSeconds)})`}
              />
            ))}
          </div>

          {/* Legend Badges */}
          <div className="flex items-center gap-3 flex-wrap pt-0.5">
            {speakerStats.airtime.map((spk, idx) => (
              <div
                key={idx}
                className="flex items-center gap-1.5 text-xs text-slate-300 font-medium"
              >
                <span className={`w-2.5 h-2.5 rounded-full ${spk.colorTheme.avatarBg}`} />
                <span>{spk.speaker}</span>
                <span className="text-slate-500 font-mono text-[10px]">({spk.percentage}%)</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Synchronized Diarized Turns Feed */}
      {filteredSegments.length === 0 ? (
        <div className="p-10 text-center border border-dashed border-[#27272A] rounded-xl space-y-2">
          <FileText className="w-8 h-8 text-slate-500 mx-auto" />
          <p className="text-xs text-slate-400">
            {searchQuery
              ? `No spoken turns found matching "${searchQuery}".`
              : 'Transcript is not available yet.'}
          </p>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="space-y-3 max-h-[580px] overflow-y-auto pr-2 scrollbar-thin"
        >
          {filteredSegments.map((tr) => {
            const isActive = activeSegmentId === tr.id;
            const theme = getSpeakerColorTheme(tr.speaker);
            const initials = getSpeakerInitials(tr.speaker);

            return (
              <div
                key={tr.id}
                ref={(el) => {
                  if (el) segmentRefs.current.set(tr.id, el);
                  else segmentRefs.current.delete(tr.id);
                }}
                onClick={() => onSeek(tr.start_time)}
                className={`p-4 rounded-xl border transition-all duration-150 cursor-pointer space-y-2 ${
                  isActive
                    ? 'bg-[#1e1b4b]/40 border-[#8B5CF6] shadow-md shadow-[#8B5CF6]/10 ring-1 ring-[#8B5CF6]/40'
                    : 'bg-[#18181b] border-[#27272A] hover:border-[#8B5CF6]/40 hover:bg-[#1a1a22]'
                }`}
              >
                {/* Speaker Avatar + Name + Timestamp Seek Button */}
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2.5">
                    {/* Deterministic Initial Avatar */}
                    <div
                      className={`w-7 h-7 rounded-lg ${theme.avatarBg} flex items-center justify-center text-[11px] font-black text-white shadow-sm shrink-0`}
                    >
                      {initials}
                    </div>
                    <span className={`font-bold ${theme.text}`}>{tr.speaker}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    {isActive && (
                      <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20 animate-pulse">
                        <Volume2 className="w-3 h-3" />
                        <span>PLAYING</span>
                      </span>
                    )}

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSeek(tr.start_time);
                      }}
                      title="Jump audio to this second"
                      className="text-[11px] font-mono text-[#8B5CF6] hover:text-white bg-[#8B5CF6]/10 hover:bg-[#8B5CF6] px-2.5 py-0.5 rounded-lg border border-[#8B5CF6]/20 transition-colors cursor-pointer flex items-center gap-1 font-semibold"
                    >
                      <Play className="w-2.5 h-2.5 fill-current" />
                      <span>@{formatTimeSeconds(tr.start_time)}</span>
                    </button>
                  </div>
                </div>

                {/* Spoken Text with Search Query Highlight */}
                <p className="text-xs sm:text-sm text-slate-200 leading-relaxed pl-9">
                  {highlightText(tr.text, searchQuery)}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
