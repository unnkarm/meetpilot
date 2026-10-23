import { createContext, useContext, useCallback } from 'react';
import { romanizeMeetingText, MEETING_LANGUAGES } from '../../utils/meetingLanguage';
import type { DisplayScript } from '../../utils/meetingLanguage';

export const MeetingScriptContext = createContext<DisplayScript>('original');
export function useMeetingText() {
  const script = useContext(MeetingScriptContext);
  return useCallback((text: string | null | undefined) =>
    script === 'romanized' ? romanizeMeetingText(text || '') : (text || ''), [script]);
}

export function MeetingLanguageSelect({ value, onChange, disabled = false }: {
  value: string; onChange: (language: string) => void; disabled?: boolean;
}) {
  return <label className="block space-y-2 text-sm text-ink">
    <span>Meeting language</span>
    <select value={value} onChange={e => onChange(e.target.value)} disabled={disabled}
      className="w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-ink disabled:opacity-50">
      {MEETING_LANGUAGES.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
    </select>
    <span className="block text-sm text-muted">Choose the main spoken language, or Auto-detect for a mixed-language meeting.</span>
  </label>;
}
