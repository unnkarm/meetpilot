import React, { useState, useEffect } from 'react';
import {
  Search,
  FileText,
  Mic,
  CheckSquare,
  Scale,
  Calendar,
  Clock,
  ArrowRight,
  Filter,
  Sparkles,
  Layers,
  ExternalLink,
} from 'lucide-react';
import { ApiWorkspace, ApiWorkspaceSearchResult } from '../../types';
import { searchWorkspaceExtendedApi } from '../../services/api';

interface WorkspaceSemanticSearchProps {
  activeWorkspace: ApiWorkspace | null;
  getToken: () => Promise<string | null>;
  onNavigateToMeeting?: (meetingId: string, timestampSeconds?: number) => void;
  onNavigateToTab?: (tab: string) => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export const WorkspaceSemanticSearch: React.FC<WorkspaceSemanticSearchProps> = ({
  activeWorkspace,
  getToken,
  onNavigateToMeeting,
  onNavigateToTab,
  showToast,
}) => {
  const workspaceId = activeWorkspace?.id || null;
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [searchResults, setSearchResults] = useState<ApiWorkspaceSearchResult[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const filterOptions = [
    { id: 'all', label: 'All Knowledge', icon: Layers },
    { id: 'meetings', label: 'Meetings & Audio', icon: Mic },
    { id: 'documents', label: 'Company Documents', icon: FileText },
    { id: 'tasks', label: 'Action Items', icon: CheckSquare },
    { id: 'decisions', label: 'Decisions', icon: Scale },
  ];

  const handleSearch = async (queryToUse?: string, filterToUse?: string) => {
    const q = (queryToUse !== undefined ? queryToUse : searchQuery).trim();
    const f = filterToUse !== undefined ? filterToUse : filterType;
    if (!q || !workspaceId) return;

    setIsSearching(true);
    setHasSearched(true);

    try {
      const response = await searchWorkspaceExtendedApi(q, workspaceId, f, getToken);
      setSearchResults(response.results || []);
      setTotalCount(response.total_results || 0);
    } catch (err: any) {
      showToast(`Search failed: ${err.message || 'Server error'}`, 'error');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const parseTimestampToSeconds = (ts?: string | null): number | undefined => {
    if (!ts) return undefined;
    const parts = ts.split(':').map(Number);
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    return undefined;
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'transcript':
        return (
          <span className="px-2 py-0.5 rounded-full text-sm font-mono bg-rose-500/10 text-rose-700 border border-rose-500/20 flex items-center gap-1">
            <Mic className="w-2.5 h-2.5" /> Meeting Transcript
          </span>
        );
      case 'document':
        return (
          <span className="px-2 py-0.5 rounded-full text-sm font-mono bg-sky-500/10 text-sky-700 border border-sky-500/20 flex items-center gap-1">
            <FileText className="w-2.5 h-2.5" /> Knowledge Document
          </span>
        );
      case 'task':
        return (
          <span className="px-2 py-0.5 rounded-full text-sm font-mono bg-emerald-500/10 text-emerald-700 border border-emerald-500/20 flex items-center gap-1">
            <CheckSquare className="w-2.5 h-2.5" /> Action Item
          </span>
        );
      case 'decision':
        return (
          <span className="px-2 py-0.5 rounded-full text-sm font-mono bg-amber-500/10 text-amber-700 border border-amber-500/20 flex items-center gap-1">
            <Scale className="w-2.5 h-2.5" /> Decision
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-sm font-mono bg-brand/10 text-brand border border-brand/20">
            Meeting
          </span>
        );
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-y-auto bg-canvas p-4 sm:p-6 max-w-6xl mx-auto w-full">
      {/* Top Banner */}
      <div className="mb-6 space-y-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-brand/20 border border-brand/40 flex items-center justify-center">
            <Search className="w-4 h-4 text-brand" />
          </div>
          <h1 className="text-xl font-bold text-ink">Search your workspace</h1>
        </div>
        <p className="text-sm text-muted">
          Find conversations, documents, action items and decisions by meaning or keyword.
        </p>
      </div>

      {/* Search Input Bar */}
      <div className="bg-surface border border-line rounded-xl p-4 shadow-sm mb-6 space-y-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
          className="flex items-center gap-2"
        >
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-muted absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              aria-label="Search workspace knowledge"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search concepts, technical specs, budget constraints, decisions, or exact IDs..."
              className="w-full pl-11 pr-4 py-3 rounded-xl bg-surface border border-line text-sm sm:text-sm text-ink placeholder-slate-500 focus:outline-none focus:border-brand transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={isSearching || !searchQuery.trim()}
            className="px-5 py-3 rounded-xl bg-brand hover:bg-brand disabled:opacity-50 text-on-brand text-sm sm:text-sm font-bold flex items-center gap-2 transition-all cursor-pointer shadow-sm  shrink-0"
          >
            <Sparkles className="w-4 h-4" />
            <span>Search</span>
          </button>
        </form>

        {/* Category Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-line">
          <span className="text-sm font-mono uppercase text-muted mr-2 flex items-center gap-1">
            <Filter className="w-3 h-3" /> Filter:
          </span>
          {filterOptions.map((opt) => {
            const Icon = opt.icon;
            const isSelected = filterType === opt.id;
            return (
              <button
                key={opt.id}
                onClick={() => {
                  setFilterType(opt.id);
                  if (searchQuery.trim()) {
                    handleSearch(searchQuery, opt.id);
                  }
                }}
                className={`px-3 py-1.5 rounded-lg text-sm font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-brand text-on-brand shadow-md '
                    : 'bg-surface hover:bg-line text-muted hover:text-ink border border-line'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{opt.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Results Header */}
      {hasSearched && (
        <div className="flex items-center justify-between mb-4">
          <div className="text-sm text-muted font-mono">
            Found <span className="text-ink font-bold">{totalCount}</span> relevant result(s) for "
            <span className="text-brand">{searchQuery}</span>"
          </div>
        </div>
      )}

      {/* Results List */}
      {isSearching ? (
        <div className="py-16 text-center space-y-3">
          <div className="w-8 h-8 rounded-full border-2 border-brand border-t-transparent animate-spin mx-auto" />
          <div className="text-sm text-muted font-mono">Computing vector similarity & scanning workspace data...</div>
        </div>
      ) : !hasSearched ? (
        <div className="py-16 text-center border border-dashed border-line rounded-xl p-8 space-y-3">
          <div className="w-12 h-12 rounded-xl bg-surface border border-line flex items-center justify-center mx-auto text-muted">
            <Search className="w-6 h-6" />
          </div>
          <h2 className="text-sm font-bold text-ink">Search Everything Across Your Workspace</h2>
          <p className="text-sm text-muted max-w-md mx-auto">
            Type keywords, concepts, or exact terms to perform high-precision hybrid vector semantic search across your entire workspace memory.
          </p>
        </div>
      ) : searchResults.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-line rounded-xl p-8 space-y-2">
          <div className="text-sm font-bold text-ink">No matching knowledge found</div>
          <p className="text-sm text-muted max-w-sm mx-auto">
            Try adjusting your query or upload more company documents and record meetings to expand workspace memory.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {searchResults.map((res, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl bg-surface border border-line hover:border-brand/50 transition-all group space-y-2.5"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2 flex-wrap">
                  {getTypeBadge(res.type)}
                  <span className="text-sm font-bold text-ink group-hover:text-brand transition-colors">
                    {res.document_title || res.meeting_title || 'Workspace Result'}
                  </span>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {res.timestamp && (
                    <span className="px-2 py-0.5 rounded bg-line text-sm font-mono text-ink">
                      @{res.timestamp}
                    </span>
                  )}
                  {res.page_number && (
                    <span className="px-2 py-0.5 rounded bg-line text-sm font-mono text-ink">
                      Page {res.page_number}
                    </span>
                  )}
                  {res.speaker && (
                    <span className="px-2 py-0.5 rounded bg-line text-sm font-mono text-brand">
                      {res.speaker}
                    </span>
                  )}
                </div>
              </div>

              <div className="text-sm text-ink leading-relaxed font-mono bg-surface p-3 rounded-lg border border-line">
                {res.snippet}
              </div>

              {/* Action Jump Button */}
              <div className="flex justify-end pt-1">
                {['transcript', 'decision'].includes(res.type) && res.meeting_id && onNavigateToMeeting && (
                  <button
                    onClick={() =>
                      onNavigateToMeeting(res.meeting_id!, parseTimestampToSeconds(res.timestamp))
                    }
                    className="text-sm text-brand hover:text-brand font-bold flex items-center gap-1 cursor-pointer transition-colors"
                  >
                    <span>Open meeting at timestamp</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                )}
                {res.type === 'meeting' && res.meeting_id && onNavigateToMeeting && (
                  <button
                    onClick={() => onNavigateToMeeting(res.meeting_id!)}
                    className="text-sm text-brand hover:text-brand font-bold flex items-center gap-1 cursor-pointer transition-colors"
                  >
                    <span>View meeting details</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                )}
                {res.type === 'task' && onNavigateToTab && (
                  <button
                    onClick={() => onNavigateToTab('kanban')}
                    className="text-sm text-emerald-700 hover:text-emerald-700 font-bold flex items-center gap-1 cursor-pointer transition-colors"
                  >
                    <span>View in Kanban Board</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
