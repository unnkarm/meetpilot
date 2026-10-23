import { useEffect, useState } from 'react';
import { useMeetingText } from './MeetingLanguageDisplay';

type Insight = {
  kind: string;
  text: string;
  speaker: string;
  timestamp: number;
  source_quote: string;
  source_segment_id: string;
  related_source?: { title?: string; timestamp?: string; speaker?: string; snippet?: string };
};

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function LiveInsights({ meetingId, getToken }: {
  meetingId: string; getToken: () => Promise<string | null>;
}) {
  const displayText = useMeetingText();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [connected, setConnected] = useState(false);
  const [botStatus, setBotStatus] = useState('Bot is queued');

  useEffect(() => {
    let cancelled = false;
    let socket: WebSocket | undefined;
    void (async () => {
      const token = await getToken();
      if (!token || cancelled) return;
      const endpoint = new URL(API_BASE);
      endpoint.protocol = endpoint.protocol === 'https:' ? 'wss:' : 'ws:';
      endpoint.pathname = `/api/v1/meetings/live/${meetingId}/insights`;
      socket = new WebSocket(endpoint.toString());
      socket.onopen = () => { socket?.send(JSON.stringify({ token })); setConnected(true); };
      socket.onclose = () => setConnected(false);
      socket.onmessage = event => {
        const item = JSON.parse(event.data) as Insight;
        if (item.kind === 'heartbeat') return;
        if (item.kind === 'bot_status') { setBotStatus(item.text); return; }
        setInsights(previous => [item, ...previous.filter(old => old.source_segment_id !== item.source_segment_id || old.kind !== item.kind)].slice(0, 8));
      };
    })();
    return () => { cancelled = true; socket?.close(); };
  }, [meetingId, getToken]);

  return <section className="rounded-xl border border-brand/30 bg-surface p-4 space-y-3">
    <div className="flex items-center justify-between">
      <h3 className="font-semibold text-ink">Live co-pilot insights</h3>
      <span className="text-sm text-muted">{connected ? 'Listening' : 'Connecting'}</span>
    </div>
    <p className="text-sm text-brand" role="status">{botStatus}</p>
    {insights.length === 0 && <p className="text-sm text-muted">Evidence-linked alerts will appear as the meeting progresses.</p>}
    {insights.map(item => <div key={`${item.kind}:${item.source_segment_id}`} className="border-t border-line pt-2">
      <p className="text-sm text-ink">{displayText(item.text)}</p>
      <p className="text-sm text-muted">{item.speaker} · {Math.floor(item.timestamp / 60).toString().padStart(2, '0')}:{Math.floor(item.timestamp % 60).toString().padStart(2, '0')}</p>
      <p className="text-sm text-ink" title={item.source_quote}>“{displayText(item.source_quote)}”</p>
      {item.related_source && <p className="text-sm text-brand">Related: {item.related_source.title || 'Workspace knowledge'}{item.related_source.timestamp ? ` · ${item.related_source.timestamp}` : ''}{item.related_source.speaker ? ` · ${item.related_source.speaker}` : ''}</p>}
    </div>)}
  </section>;
}
