import { svelte } from '@sveltejs/vite-plugin-svelte';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { resolve } from 'node:path';
import { type Plugin } from 'vite';
import { defineConfig } from 'vitest/config';

// In development /data/*.json comes from a workspace's _meta/data (or the golden fixture).
// In a built console the same URLs are served by the sw-view server.
function serveData(): Plugin {
  const dir = resolve(process.env.DATA_DIR ?? '../_meta/data');
  return {
    name: 'specwright-data',
    configureServer(server) {
      server.middlewares.use('/data', (req, res, next) => {
        const name = (req.url ?? '').split('?')[0].replace(/^\/+/, '');
        const file = resolve(dir, name);
        if (!/^[a-z]+\.json$/.test(name) || !file.startsWith(dir) || !existsSync(file) || !statSync(file).isFile()) {
          next();
          return;
        }
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.setHeader('Cache-Control', 'no-store');
        createReadStream(file).pipe(res);
      });
    },
  };
}

export default defineConfig({
  base: './',
  plugins: [svelte(), serveData()],
  build: {
    target: 'es2022',
    assetsInlineLimit: 0,
    cssCodeSplit: false,
    sourcemap: false,
    modulePreload: { polyfill: false },
  },
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
  },
});
