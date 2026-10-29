import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// Fully static build, served as Cloudflare Workers static assets (see wrangler.jsonc).
export default defineConfig({
  site: 'https://aajkamandi.com',
  trailingSlash: 'always',
  build: { format: 'directory' },
  // lastmod = build time: data sites rebuild when data changes, static sites only when edited
  integrations: [sitemap({ lastmod: new Date() })],
});
