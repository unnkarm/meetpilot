import React, { useEffect, useMemo, useState } from 'react';
import useSWR from 'swr';
import { Copy, Loader2, Plus, Sparkles, Trash2 } from 'lucide-react';
import { apiFetch } from '../../services/api';
import type { ApiTranscriptSegment } from '../../types';
import type { ReviewArtifact, ReviewPoint, ReviewMetrics, ReviewRisk, SummaryTemplate } from '../../types/review';
import { formatTimeSeconds } from '../../utils/speakerUtils';
import { MeetingBookmarks } from './MeetingBookmarks';
import { useMeetingText } from './MeetingLanguageDisplay';

interface Props {
  meetingId: string; workspaceId: string; actorId: string; getToken: () => Promise<string | null>;
  currentTime: number; segments: ApiTranscriptSegment[]; onSeek: (seconds: number) => void;
}
const control = 'rounded-lg border border-line bg-surface p-2 text-sm text-ink';
const button = 'rounded-lg bg-brand px-3 py-2 text-sm font-semibold text-on-brand disabled:opacity-40';
const box = 'rounded-xl border border-line bg-surface p-5 space-y-4';

export function MeetingReviewTools({ meetingId, workspaceId, actorId, getToken, currentTime, segments, onSeek }: Props) {
  const root = `/api/v1/meetings/${meetingId}/review`;
  const templatesPath = `/api/v1/workspaces/${workspaceId}/summary-templates`;
  const fetcher = <T,>([url]: [string, string]) => apiFetch<T>(url, {}, getToken);
  const templates = useSWR<{ templates: SummaryTemplate[]; can_manage: boolean }>([templatesPath, actorId], fetcher);
  const artifacts = useSWR<ReviewArtifact[]>([`${root}/artifacts`, actorId], fetcher, {
    refreshInterval: rows => rows?.some(a => a.status === 'queued' || a.status === 'processing') ? 3000 : 0,
  });
  const metrics = useSWR<ReviewMetrics>([`${root}/metrics`, actorId], fetcher);
  const risks = useSWR<{ risks: ReviewRisk[]; note: string }>([`${root}/risks`, actorId], fetcher);
  const [selected, setSelected] = useState<string | null>(null);
  const detail = useSWR<ReviewArtifact>(selected ? [`${root}/artifacts/${selected}`, actorId] : null, fetcher,
    { refreshInterval: row => row?.status === 'queued' || row?.status === 'processing' ? 3000 : 0 });
  const [kind, setKind] = useState<ReviewArtifact['kind']>('summary');
  const [templateId, setTemplateId] = useState('executive');
  const [format, setFormat] = useState('email');
  const [audience, setAudience] = useState('internal');
  const [language, setLanguage] = useState('meeting');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [draft, setDraft] = useState('');
  const [templateName, setTemplateName] = useState('');
  const [instructions, setInstructions] = useState('');
  const [editingTemplate, setEditingTemplate] = useState<string | null>(null);
  const [hourlyRate, setHourlyRate] = useState('');
  const [participantCount, setParticipantCount] = useState('');
  const displayText = useMeetingText();
  const payload = detail.data?.status === 'completed' ? detail.data.payload : null;
  const plainText = useMemo(() => {
    if (!payload) return '';
    return displayText([payload.subject || '', ...payload.sections.flatMap(section => [section.title, ...section.points.map(p => p.text)]),
      ...payload.paragraphs.map(p => p.text), ...payload.chapters.flatMap(chapter => [`${formatTimeSeconds(chapter.start_time)} ${chapter.title}`, ...chapter.points.map(p => p.text)])].filter(Boolean).join('\n\n'));
  }, [payload, displayText]);
  useEffect(() => { setDraft(plainText); setCopied(false); }, [plainText, selected]);
  useEffect(() => {
    if (!selected && artifacts.data?.length) setSelected(artifacts.data[0].id);
  }, [artifacts.data, selected]);
  const generate = async () => {
    setBusy(true); setError('');
    try {
      const item = await apiFetch<ReviewArtifact>(`${root}/artifacts`, { method: 'POST', body: JSON.stringify({ id: crypto.randomUUID(), kind, template_id: templateId, format, audience, language }) }, getToken);
      setSelected(item.id); await artifacts.mutate();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not generate draft.'); }
    finally { setBusy(false); }
  };
  const retry = async () => {
    if (!selected) return;
    setBusy(true); setError('');
    try { await apiFetch(`${root}/artifacts/${selected}/retry`, { method: 'POST' }, getToken); await Promise.all([artifacts.mutate(), detail.mutate()]); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not retry draft.'); }
    finally { setBusy(false); }
  };
  const removeDraft = async (id: string) => {
    setBusy(true); setError('');
    try { await apiFetch(`${root}/artifacts/${id}`, { method: 'DELETE' }, getToken); const rows = await artifacts.mutate(); if (id === selected) setSelected(rows?.[0]?.id || null); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not remove draft.'); }
    finally { setBusy(false); }
  };
  const saveTemplate = async () => {
    setBusy(true); setError('');
    try {
      const item = await apiFetch<SummaryTemplate>(editingTemplate ? `${templatesPath}/${editingTemplate}` : templatesPath,
        { method: editingTemplate ? 'PATCH' : 'POST', body: JSON.stringify({ name: templateName, instructions }) }, getToken);
      setTemplateId(item.id); setEditingTemplate(null); setTemplateName(''); setInstructions(''); await templates.mutate();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not save template.'); }
    finally { setBusy(false); }
  };
  const deleteTemplate = async (id: string) => {
    setBusy(true); setError('');
    try { await apiFetch(`${templatesPath}/${id}`, { method: 'DELETE' }, getToken); if (templateId === id) setTemplateId('executive'); await templates.mutate(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not delete template.'); }
    finally { setBusy(false); }
  };
  const citedPoint = (point: ReviewPoint, index: number) => <li key={index} className="space-y-1">
    <p className="text-sm text-ink">{displayText(point.text)}</p>
    <div className="flex flex-wrap gap-2">{point.source_ids.map(id => {
      const cite = payload?.citations[id];
      return cite ? <button key={id} onClick={() => onSeek(cite.start_time)} title={cite.quote} className="text-sm text-brand hover:text-brand">{formatTimeSeconds(cite.start_time)} · {displayText(cite.speaker)}</button> : null;
    })}</div>
  </li>;
  const estimate = metrics.data && Number(hourlyRate) > 0 && Number(hourlyRate) <= 1000000 && Number.isInteger(Number(participantCount)) && Number(participantCount) > 0 && Number(participantCount) <= 1000
    ? (metrics.data.duration_seconds / 3600 * Number(hourlyRate) * Number(participantCount)).toFixed(2) : null;
  const loadError = templates.error || artifacts.error || detail.error || metrics.error || risks.error;
  return <div className="space-y-6">
    <section className={box}>
      <h3 className="font-semibold text-ink flex items-center gap-2"><Sparkles className="w-4 h-4 text-brand" />Evidence-linked review drafts</h3>
      <p className="text-sm text-muted">Drafts are private to you. Your original meeting summary stays available. Review the sources before sharing.</p>
      <div className="flex flex-wrap gap-3">
        <select aria-label="Review format" value={kind} onChange={e => setKind(e.target.value as ReviewArtifact['kind'])} className={control}><option value="summary">Summary lens</option><option value="followup">Follow-up draft</option><option value="chapters">Timeline chapters</option></select>
        {kind === 'summary' && <select aria-label="Summary template" className={control} value={templateId} onChange={e => setTemplateId(e.target.value)}>{templates.data?.templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select>}
        {kind === 'followup' && <><select aria-label="Follow-up format" value={format} onChange={e => setFormat(e.target.value)} className={control}><option value="email">Email</option><option value="slack">Slack digest</option><option value="teams">Teams digest</option></select><select aria-label="Audience" value={audience} onChange={e => setAudience(e.target.value)} className={control}><option value="internal">Internal team</option><option value="client">Client</option></select></>}
        <select aria-label="Draft language" value={language} onChange={e => setLanguage(e.target.value)} className={control}><option value="meeting">Meeting language</option><option value="en">English</option><option value="bn">Bengali</option><option value="hi">Hindi</option></select>
        <button onClick={() => void generate()} disabled={busy || !segments.length} className={button}>Generate draft</button>
      </div>
      {(error || loadError) && <p role="alert" className="text-sm text-rose-700">{error || loadError.message}</p>}
      {templates.data?.can_manage && <details className="text-sm text-ink">
        <summary className="cursor-pointer">Manage workspace templates</summary>
        <div className="mt-3 space-y-3">
          {templates.data.templates.filter(t => !t.builtin).map(t => <div key={t.id} className="flex items-center gap-3"><span>{t.name}</span><button onClick={() => { setEditingTemplate(t.id); setTemplateName(t.name); setInstructions(t.instructions); }} className="text-sm text-brand">Edit</button><button aria-label={`Delete template ${t.name}`} disabled={busy} onClick={() => void deleteTemplate(t.id)} className="text-rose-700"><Trash2 className="w-3 h-3" /></button></div>)}
          <input aria-label="Template name" placeholder="Template name" maxLength={80} className={`${control} w-full`} value={templateName} onChange={e => setTemplateName(e.target.value)} />
          <textarea aria-label="Template instructions" placeholder="Describe the sections and focus. Only supported meeting facts will be included." maxLength={2000} className={`${control} w-full`} rows={3} value={instructions} onChange={e => setInstructions(e.target.value)} />
          <button disabled={busy || templateName.trim().length < 3 || instructions.trim().length < 10} onClick={() => void saveTemplate()} className={button}><Plus className="inline w-3 h-3 mr-1" />{editingTemplate ? 'Save template' : 'Add template'}</button>
          {editingTemplate && <button onClick={() => { setEditingTemplate(null); setTemplateName(''); setInstructions(''); }} className="ml-3 text-sm">Cancel edit</button>}
        </div>
      </details>}
    </section>
    {!!artifacts.data?.length && <section className={box}>
      <div className="flex items-center gap-3"><select aria-label="Saved review draft" className={`${control} flex-1 min-w-0`} value={selected || ''} onChange={e => setSelected(e.target.value)}>{artifacts.data.map(a => <option key={a.id} value={a.id}>{a.options.template_name || (a.kind === 'followup' ? `${a.options.format} · ${a.options.audience}` : 'Chapters')} · {a.status}</option>)}</select><button aria-label="Delete or cancel selected draft" disabled={busy || !selected} onClick={() => selected && void removeDraft(selected)} className="text-rose-700 p-2"><Trash2 className="w-4 h-4" /></button></div>
      {detail.data && (detail.data.status === 'queued' || detail.data.status === 'processing') && <div className="text-sm text-brand flex gap-2 items-center"><Loader2 className="w-4 h-4 animate-spin" />{detail.data.status === 'queued' ? 'Waiting for the processing worker…' : `Generating from saved speech${detail.data.progress?.total ? ` · ${detail.data.progress.completed}/${detail.data.progress.total} sections processed` : '…'}`}</div>}
      {detail.data?.failure_reason && <p role="alert" className="text-sm text-rose-700">{detail.data.failure_reason}</p>}
      {detail.data?.stale && <p className="text-sm text-amber-700">The transcript changed since this draft was created. Regenerate before using it.</p>}
      {detail.data && <button onClick={() => void retry()} disabled={busy} className="text-sm text-brand">{detail.data.status === 'completed' ? 'Regenerate from current transcript' : 'Retry failed or stale job'}</button>}
      {payload && <>
        {payload.sections.map((section, index) => <div key={index} className="space-y-2"><h4 className="font-semibold text-ink">{displayText(section.title)}</h4><ul className="space-y-3">{section.points.map(citedPoint)}</ul></div>)}
        {!!payload.paragraphs.length && <ul className="space-y-3">{payload.paragraphs.map(citedPoint)}</ul>}
        {payload.chapters.map((chapter, index) => <div key={index} className="space-y-2"><button onClick={() => onSeek(chapter.start_time)} className="font-semibold text-brand">{formatTimeSeconds(chapter.start_time)} — {displayText(chapter.title)}</button><ul className="space-y-3">{chapter.points.map(citedPoint)}</ul></div>)}
        <p className="text-sm text-muted">Processed {payload.coverage.segments} saved speech turns. Source links support review; AI accuracy is not guaranteed.</p>
        <label className="block text-sm text-ink">Editable copy for sharing<textarea aria-label="Editable review draft" className={`${control} mt-2 w-full`} rows={8} value={draft} onChange={e => { setDraft(e.target.value); setCopied(false); }} /></label>
        <button onClick={async () => { try { await navigator.clipboard.writeText(draft); setCopied(true); } catch { setError('Clipboard unavailable. Select and copy the draft text.'); } }} className={button}><Copy className="inline w-3 h-3 mr-1" />{copied ? 'Copied' : 'Copy draft'}</button><p className="text-sm text-muted">Edits in this copy are not saved. Copying does not send a message to anyone.</p>
      </>}
    </section>}
    <MeetingBookmarks meetingId={meetingId} actorId={actorId} getToken={getToken} position={currentTime} hasTranscript={!!segments.length} onSeek={onSeek} />
    <section className={box}><h3 className="font-semibold text-ink">Risk and blocker review</h3><p className="text-sm text-muted">{risks.data?.note}</p>
      {risks.data?.risks.length === 0 && <p className="text-sm text-muted">No missing task metadata or cited blockers found in your accessible records.</p>}
      {risks.data?.risks.map(risk => <div key={risk.id} className="rounded-lg border border-amber-500/20 p-3 space-y-1"><p className="text-sm text-ink">{displayText(risk.title)}</p><p className="text-sm text-amber-700">{risk.reasons.join(' · ')}</p>{risk.quote && <p className="text-sm text-muted">“{displayText(risk.quote)}” {risk.speaker && `— ${displayText(risk.speaker)}`}</p>}{risk.source_segment_id && <button className="text-sm text-brand" onClick={() => { const source = segments.find(s => s.id === risk.source_segment_id); if (source) onSeek(source.start_time); }}>Review source speech</button>}</div>)}
    </section>
    <section className={box}><h3 className="font-semibold text-ink">Speaking metrics</h3><p className="text-sm text-muted">Speech: {formatTimeSeconds(metrics.data?.speech_seconds || 0)} · Transcript gaps: {formatTimeSeconds(metrics.data?.silence_seconds || 0)} · Overlap: {formatTimeSeconds(metrics.data?.overlap_speaker_seconds || 0)} speaker-seconds</p>
      <div className="overflow-x-auto"><table className="w-full text-sm text-left text-ink"><thead><tr className="text-muted">{['Speaker', 'Talk share', 'Words/min', 'Fillers', 'Questions', 'Longest turn'].map(h => <th key={h} className="p-2">{h}</th>)}</tr></thead><tbody>{metrics.data?.speakers.map(s => <tr key={s.speaker} className="border-t border-line"><td className="p-2">{displayText(s.speaker)}</td><td className="p-2">{s.talk_share_percent}%</td><td className="p-2">{s.words_per_minute ?? '—'}</td><td className="p-2">{s.fillers}</td><td className="p-2">{s.questions}</td><td className="p-2">{formatTimeSeconds(s.longest_monologue_seconds)}{s.monologues_over_90s > 0 && ' · long monologue'}</td></tr>)}</tbody></table></div>
      {metrics.data?.notes.map(note => <p key={note} className="text-sm text-muted">{note}</p>)}
      <details className="text-sm text-ink"><summary className="cursor-pointer">Estimate meeting cost</summary><div className="mt-3 flex flex-wrap gap-3"><input aria-label="Average hourly cost per participant" type="number" min="0" step="0.01" value={hourlyRate} onChange={e => setHourlyRate(e.target.value)} placeholder="Hourly cost/person" className={control} /><input aria-label="Participant count for estimate" type="number" min="1" max="1000" step="1" value={participantCount} onChange={e => setParticipantCount(e.target.value)} placeholder="Participants" className={control} />{estimate && <p className="text-sm text-brand py-2">Estimated cost: {estimate} in your rate's currency</p>}</div><p className="mt-2 text-sm text-muted">Uses your assumptions × meeting duration. These inputs are not saved and do not measure ROI or employee performance.</p></details>
    </section>
  </div>;
}
