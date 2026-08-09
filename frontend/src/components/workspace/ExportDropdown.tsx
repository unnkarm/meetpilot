import React, { useState, useRef, useEffect } from 'react';
import { Download, FileCode, FileText, Printer, ChevronDown } from 'lucide-react';

interface ExportDropdownProps {
  onExportMarkdown: () => void;
  onExportJSON: () => void;
  onExportPDF: () => void;
}

export const ExportDropdown: React.FC<ExportDropdownProps> = ({
  onExportMarkdown,
  onExportJSON,
  onExportPDF,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-3.5 py-2 rounded-xl bg-[#18181b] hover:bg-[#27272A] text-slate-200 hover:text-white border border-[#27272A] text-xs font-bold flex items-center gap-2 transition-all cursor-pointer shadow-sm active:scale-95"
      >
        <Download className="w-3.5 h-3.5 text-[#8B5CF6]" />
        <span>Export</span>
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-52 rounded-xl bg-[#18181b] border border-[#27272A] shadow-2xl py-1.5 z-50 animate-fadeIn divide-y divide-[#27272A]">
          <div className="p-1 space-y-0.5">
            <button
              onClick={() => {
                onExportMarkdown();
                setIsOpen(false);
              }}
              className="w-full text-left px-3 py-2 text-xs font-semibold text-slate-200 hover:text-white hover:bg-[#27272A] rounded-lg flex items-center gap-2.5 transition-colors cursor-pointer"
            >
              <FileCode className="w-4 h-4 text-[#8B5CF6]" />
              <div>
                <div>Markdown Summary</div>
                <div className="text-[10px] text-slate-500 font-normal">Formatted briefing doc (.md)</div>
              </div>
            </button>

            <button
              onClick={() => {
                onExportJSON();
                setIsOpen(false);
              }}
              className="w-full text-left px-3 py-2 text-xs font-semibold text-slate-200 hover:text-white hover:bg-[#27272A] rounded-lg flex items-center gap-2.5 transition-colors cursor-pointer"
            >
              <FileText className="w-4 h-4 text-cyan-400" />
              <div>
                <div>JSON Schema</div>
                <div className="text-[10px] text-slate-500 font-normal">Raw segments & tasks (.json)</div>
              </div>
            </button>

            <button
              onClick={() => {
                onExportPDF();
                setIsOpen(false);
              }}
              className="w-full text-left px-3 py-2 text-xs font-semibold text-slate-200 hover:text-white hover:bg-[#27272A] rounded-lg flex items-center gap-2.5 transition-colors cursor-pointer"
            >
              <Printer className="w-4 h-4 text-emerald-400" />
              <div>
                <div>Print / PDF</div>
                <div className="text-[10px] text-slate-500 font-normal">Executive print layout</div>
              </div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
