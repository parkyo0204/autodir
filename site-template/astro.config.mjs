import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://dashboard.zxzx.app',
  output: 'static',
  build: {
    format: 'directory',
  },
});
