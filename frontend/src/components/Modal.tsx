import { useEffect, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';
export function Modal({ label, onClose, children, className = '', busy = false }: { label: string; onClose: () => void; children: ReactNode; className?: string; busy?: boolean }) {
  const panel = useRef<HTMLDivElement>(null);
  const close = useRef(onClose); close.current = onClose;
  const isBusy = useRef(busy); isBusy.current = busy;
  useEffect(() => {
    const before = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    panel.current?.focus();
    function key(e: KeyboardEvent) {
      const dialogs = document.querySelectorAll('[role="dialog"]');
      if (dialogs[dialogs.length - 1] !== panel.current) return;
      if (e.key === 'Escape' && !isBusy.current) close.current();
      if (e.key !== 'Tab') return;
      const nodes = panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), textarea:not(:disabled), select:not(:disabled), [tabindex="0"]');
      if (!nodes?.length) return;
      if (e.shiftKey && (document.activeElement === nodes[0] || document.activeElement === panel.current)) { e.preventDefault(); nodes[nodes.length - 1].focus(); }
      else if (!e.shiftKey && document.activeElement === nodes[nodes.length - 1]) { e.preventDefault(); nodes[0].focus(); }
    }
    document.addEventListener('keydown', key);
    return () => { document.body.style.overflow = overflow; before?.focus(); document.removeEventListener('keydown', key); };
  }, []);
  return <div className="mp-dialog-backdrop" onClick={e => { if (e.target === e.currentTarget && !busy) onClose(); }}><div role="dialog" aria-modal="true" aria-label={label} ref={panel} tabIndex={-1} className={`mp-modal ${className}`}><button className="mp-icon-button mp-dialog-close" onClick={onClose} disabled={busy} aria-label="Close dialog"><X size={19} /></button>{children}</div></div>;
}
