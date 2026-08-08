import { TechStackItem } from '../types';

export const TECH_STACK: TechStackItem[] = [
  { name: 'Gemini 2.0 Flash', role: 'Speech Diarization & Summarization', iconName: 'Sparkles', color: 'text-emerald-400' },
  { name: 'FastAPI', role: 'Async Python Backend', iconName: 'Zap', color: 'text-teal-400' },
  { name: 'Next.js / Vite', role: 'App Router & Edge UI', iconName: 'Globe', color: 'text-white' },
  { name: 'PostgreSQL', role: 'pgvector Semantic Embeddings', iconName: 'Database', color: 'text-sky-400' },
  { name: 'Redis & Celery', role: 'Background Worker Pipeline', iconName: 'Cpu', color: 'text-red-400' },
  { name: 'Clerk', role: 'Enterprise JWT Authentication', iconName: 'Box', color: 'text-blue-400' }
];
