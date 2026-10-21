import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { fileURLToPath } from 'url';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(path.dirname(fileURLToPath(import.meta.url)), '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modifyâfile watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      // Docker Desktop may miss Windows bind-mount events. Poll source files at
      // a modest interval; Vite excludes node_modules and .git from watching.
      watch: process.env.DISABLE_HMR === 'true' ? null : process.env.MEETPILOT_WATCH_POLLING === 'true'
        ? { usePolling: true, interval: 1500, binaryInterval: 3000 } : {},
    },
  };
});
