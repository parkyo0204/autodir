import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://zxzx.app',
  output: 'static',
  build: {
    format: 'directory',
  },
});
