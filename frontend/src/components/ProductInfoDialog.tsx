import { useEffect, useRef } from 'react';
import { X, ArrowRight } from 'lucide-react';
export function ProductInfoDialog({ mode, onClose, onLaunch }: { mode: 'guide' | null; onClose: () => void; onLaunch: () => void }) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!mode) return;
    const before = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden'; panel.current?.focus();
    function key(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Tab') {
        const buttons = panel.current?.querySelectorAll<HTMLButtonElement>('button');
        if (!buttons?.length) return;
        if (e.shiftKey && (document.activeElement === buttons[0] || document.activeElement === panel.current)) { e.preventDefault(); buttons[buttons.length - 1].focus(); }
        else if (!e.shiftKey && document.activeElement === buttons[buttons.length - 1]) { e.preventDefault(); buttons[0].focus(); }
      }
    }
    document.addEventListener('keydown', key);
    return () => { document.body.style.overflow = overflow; before?.focus(); document.removeEventListener('keydown', key); };
  }, [mode, onClose]);
  if (!mode) return null;
  return <div className="mp-dialog-backdrop" onClick={e => { if (e.target === e.currentTarget) onClose(); }}><div ref={panel} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="product-info-title" className="mp-info-dialog"><button className="mp-icon-button mp-dialog-close" aria-label="Close" onClick={onClose}><X size={20} /></button><p className="mp-eyebrow">MeetPilot</p><h2 id="product-info-title">Your workspace, explained.</h2><div className="mp-guide-sections"><section><h3>1. Create or join a workspace</h3><p>Create your team’s workspace or enter a join code from a manager. A join request must be approved before you can access team data.</p></section><section><h3>2. Add a meeting</h3><p>Use Join meeting for a supported live call, Record for your microphone or Upload for a recording. The host may need to admit the assistant. Select the meeting language before starting.</p></section><section><h3>3. Review the results</h3><p>Open a meeting for its summary, transcript, decisions and action items. Source timestamps open the original transcript moment. Review tools provide summary styles, chapters, bookmarks and follow-up drafts.</p></section><section><h3>4. Use your team’s knowledge</h3><p>Managers can upload company documents. Members can ask questions and follow citations. Search spans meetings, documents, decisions and the action items you can access.</p></section><section><h3>5. Configure your team</h3><p>Manage join requests in People & access. Voice settings are under Settings. Managers can connect Google Calendar, Zoom recordings and Discord in Integrations; availability depends on server configuration.</p></section><button className="mp-button mp-button-primary" onClick={onLaunch}>Open workspace <ArrowRight size={15} /></button></div></div></div>;
}
