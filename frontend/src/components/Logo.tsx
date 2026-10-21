import React from 'react';
export function MeetPilotLogo({ className = '', iconOnly = false }: { className?: string; iconOnly?: boolean }) {
  return <span className={`mp-logo ${className}`}><svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="9" fill="currentColor" /><path d="M9 20V12m7 12V8m7 12V12" stroke="white" strokeWidth="3" strokeLinecap="round" /></svg>{!iconOnly && <span>meetpilot<span className="mp-logo-dot">.</span></span>}</span>;
}
