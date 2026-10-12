import { TechStackItem } from '../types';

export const TECH_STACK: TechStackItem[] = [
  { name: 'OpenAI / Ollama / Whisper', role: 'AI and transcription providers', iconName: 'Sparkles', color: 'text-emerald-400' },
  { name: 'FastAPI', role: 'Async Python Backend', iconName: 'Zap', color: 'text-teal-400' },
  { name: 'React + Vite', role: 'Workspace interface', iconName: 'Globe', color: 'text-white' },
  { name: 'PostgreSQL', role: 'pgvector Semantic Embeddings', iconName: 'Database', color: 'text-sky-400' },
  { name: 'Redis & Celery', role: 'Background Worker Pipeline', iconName: 'Cpu', color: 'text-red-400' },
  { name: 'Clerk', role: 'Enterprise JWT Authentication', iconName: 'Box', color: 'text-blue-400' }
];
