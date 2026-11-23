// Contact form endpoint for a static Astro site on Cloudflare Workers static assets.
// POST /api/contact -> builds a plain-text email and sends it through Cloudflare Email Routing (send_email binding MAIL)
// to the site's verified destination inbox. Everything else is served from ./dist by the assets binding.
// Spam filtering: honeypot field, minimum fill time, length limits, link-count limit, and a simple per-isolate rate limit.
import { EmailMessage } from 'cloudflare:email';

const SITE = 'AajKaMandi';        // replaced at install time, e.g. "BedSizeData"
const DOMAIN = 'aajkamandi.com';         // e.g. "bedsizedata.com"
const TYPES = ['Question', 'Correction', 'Advertising or sponsorship', 'Partnership or data request', 'Other'];
const recent = new Map();            // ip -> [timestamps], best effort only

const enc = (s) => '=?UTF-8?B?' + btoa(String.fromCharCode(...new TextEncoder().encode(s))) + '?=';
const clean = (s, n) => String(s ?? '').replace(/\r/g, '').trim().slice(0, n);
const json = (status, body) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });

async function contact(request, env) {
  const ip = request.headers.get('cf-connecting-ip') || '0';
  const now = Date.now(), hits = (recent.get(ip) || []).filter((t) => now - t < 3600e3);
  if (hits.length >= 5) return json(429, { ok: false, error: 'Too many messages from this connection. Please email us instead.' });
  let f;
  try { f = await request.formData(); } catch { return json(400, { ok: false, error: 'Bad request.' }); }
  if (clean(f.get('website'), 200)) return json(200, { ok: true });                      // honeypot: bots fill it, pretend success
  const started = Number(f.get('t') || 0);
  if (!started || now - started < 3000) return json(400, { ok: false, error: 'Please take a moment before sending.' });
  const name = clean(f.get('name'), 100), email = clean(f.get('email'), 200), msg = clean(f.get('message'), 5000);
  const type = TYPES.includes(f.get('type')) ? f.get('type') : 'Other', page = clean(f.get('page'), 300);
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) return json(400, { ok: false, error: 'Please enter a valid email address.' });
  if (msg.length < 10) return json(400, { ok: false, error: 'Please write a little more.' });
  if ((msg.match(/https?:\/\//g) || []).length > 3) return json(400, { ok: false, error: 'Too many links in the message.' });
  hits.push(now); recent.set(ip, hits);

  const subject = `[${SITE}] ${type}: ${name || email}`;
  const body = `${type} from the ${SITE} contact form\n\nName: ${name || '-'}\nEmail: ${email}\nPage: ${page || '-'}\nCountry: ${request.cf?.country || '-'}\n\n${msg}\n\n--\nReply to this email to answer ${email} directly.`;
  const from = `contact-form@${DOMAIN}`, to = env.MAIL_TO;
  const raw = [
    `From: ${enc(SITE + ' contact form')} <${from}>`, `To: <${to}>`, `Reply-To: <${email}>`, `Subject: ${enc(subject)}`,
    `Message-ID: <${crypto.randomUUID()}@${DOMAIN}>`, `Date: ${new Date().toUTCString()}`,
    'MIME-Version: 1.0', 'Content-Type: text/plain; charset=UTF-8', 'Content-Transfer-Encoding: 8bit', '', body,
  ].join('\r\n');
  try {
    await env.MAIL.send(new EmailMessage(from, to, raw));
  } catch (e) {
    return json(502, { ok: false, error: `Sorry, the message could not be sent. Please email hello@${DOMAIN}.` });
  }
  return json(200, { ok: true });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/api/contact') {
      if (request.method !== 'POST') return json(405, { ok: false, error: 'Use POST.' });
      return contact(request, env);
    }
    return env.ASSETS.fetch(request);
  },
};
