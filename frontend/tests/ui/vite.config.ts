// Isolated frontend fixture server. The production Vite configuration has no auth alias.
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';
export default defineConfig({
  root: process.cwd(), plugins: [react(), tailwindcss()],
  resolve: { alias: { '@clerk/clerk-react': path.resolve('tests/ui/clerkFixture.tsx') } },
  server: { host: '127.0.0.1', port: 3011, strictPort: true, hmr: false },
});
