// Daily price-card images (1200x630 PNG) for every published mandi page.
// Used as the page's share image (WhatsApp / Facebook previews) and shown on the page.
// Run after build_site_data.py and before `astro build` (writes into public/cards/).
//
// All text is shaped with HarfBuzz and drawn as outlines (scripts/hbtext.mjs) using the bundled
// Noto Sans Devanagari (SIL OFL, fonts/OFL.txt): resvg's own shaping garbles some Hindi words.
import { Resvg } from '@resvg/resvg-js';
import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadFont, drawText } from './hbtext.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const data = JSON.parse(readFileSync(join(root, 'src/data/mandi.json'), 'utf8'));
const held = JSON.parse(readFileSync(join(root, 'src/data/holdback.json'), 'utf8'));
const out = join(root, 'public/cards');
rmSync(out, { recursive: true, force: true });
const font = loadFont(join(root, 'fonts/NotoSansDevanagari.ttf'));

const MONTHS_HI = ['जनवरी', 'फरवरी', 'मार्च', 'अप्रैल', 'मई', 'जून', 'जुलाई', 'अगस्त', 'सितंबर', 'अक्टूबर', 'नवंबर', 'दिसंबर'];
const dateHi = (iso) => { const [y, m, d] = iso.split('-').map(Number); return `${d} ${MONTHS_HI[m - 1]} ${y}`; };
const inr = (n) => Math.round(n).toLocaleString('en-IN');
const T = (text, x, y, size, opts) => drawText(font, String(text), x, y, size, opts);
// up/down arrow as a small triangle (the font has no ▲▼ glyphs)
const arrow = (up, x, y, color) => up
  ? `<polygon points="${x},${y - 4} ${x + 18},${y - 4} ${x + 9},${y - 20}" fill="${color}"/>`
  : `<polygon points="${x},${y - 20} ${x + 18},${y - 20} ${x + 9},${y - 4}" fill="${color}"/>`;

function card(t) {
  // one row per crop (first variety), most-searched crops first (rows are already priority-sorted)
  const rows = t.rows.filter((r, i, arr) => arr.findIndex((x) => x.commodity === r.commodity) === i).slice(0, 6);
  const lines = rows.map((r, i) => {
    const y = 250 + i * 58;
    const diff = r.prev_modal ? r.modal - r.prev_modal : 0;
    const color = diff > 0 ? '#1a7f37' : '#b42318';
    const change = diff === 0 ? '' :
      arrow(diff > 0, 1000, y - 6, color) + T(inr(Math.abs(diff)), 1116, y - 6, 24, { fill: color, anchor: 'end' });
    return `<rect x="60" y="${y - 44}" width="1080" height="54" rx="8" fill="${i % 2 ? '#ffffff' : '#f3f7f4'}"/>`
      + T(r.hindi ?? r.label, 84, y - 6, 32, { fill: '#17202a' })
      + T((r.variety || '').slice(0, 22), 420, y - 6, 22, { fill: '#5b6672' })
      + T(`₹${inr(r.modal)}`, 960, y - 6, 34, { weight: 700, fill: '#17202a', anchor: 'end' })
      + change;
  }).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">`
    + `<rect width="1200" height="630" fill="#ffffff"/><rect width="1200" height="150" fill="#1a7f37"/>`
    + T(`${t.town_hi ?? t.town} मंडी भाव`, 60, 82, 54, { weight: 700, fill: '#ffffff' })
    + T(`${dateHi(t.date)} · ${t.state_hi ?? t.state} · ₹ प्रति क्विंटल (मॉडल भाव)`, 60, 128, 28, { fill: '#e6f4ea' })
    + lines
    + T('स्रोत: Agmarknet (भारत सरकार)', 60, 606, 24, { fill: '#5b6672' })
    + T('aajkamandi.com', 1140, 606, 28, { weight: 700, fill: '#1a7f37', anchor: 'end' })
    + `</svg>`;
}

let n = 0;
for (const t of data.towns) {
  if (held.includes(`mandi/${t.state_slug}/${t.slug}`)) continue;
  const png = new Resvg(card(t)).render().asPng();
  const file = join(out, t.state_slug, `${t.slug}.png`);
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, png);
  n++;
}
console.log(`price cards: ${n} written to public/cards/`);
