// Brand: logo mark, homepage illustration, colours. Inline SVG only (no requests).
export const NAME = ['AajKa', 'Mandi'];
export const COLORS = { bg: '#14532d', hi: '#f59f00', accent: '#1a7f37' };
export const TAGLINE = ['Mandi bhav today', 'Official Agmarknet prices, updated hourly'];
const F = 'font-family="system-ui,Segoe UI,Arial,sans-serif"';

export const mark = (size = 34) => {
  const g = [15, 21, 27].map((y) => `<ellipse cx="16.4" cy="${y}" rx="2.5" ry="4.2" transform="rotate(-38 16.4 ${y})"/><ellipse cx="23.6" cy="${y}" rx="2.5" ry="4.2" transform="rotate(38 23.6 ${y})"/>`).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" width="${size}" height="${size}" aria-hidden="true">
<rect width="40" height="40" rx="9" fill="#1a7f37"/><path d="M20 35V12" stroke="#fde68a" stroke-width="2" stroke-linecap="round"/>
<g fill="#f59f00"><ellipse cx="20" cy="9.2" rx="2.6" ry="4.4"/>${g}</g></svg>`;
};

const sack = (x, w, h, grain) => {
  const b = 198, t = b - h, l = x - w / 2, r = x + w / 2;
  return `<path d="M${l + 7} ${b}Q${l - 7} ${b - h * 0.5} ${l + 5} ${t}H${r - 5}Q${r + 7} ${b - h * 0.5} ${r - 7} ${b}Z" fill="#cfa96f" stroke="#a8834d" stroke-width="2"/>
<path d="M${l + 2} ${b - h * 0.42}H${r - 2}" stroke="#b08a52" stroke-width="5" opacity=".6"/>
<ellipse cx="${x}" cy="${t + 1}" rx="${w / 2 - 3}" ry="11" fill="${grain}"/>
<ellipse cx="${x}" cy="${t - 3}" rx="${w / 2 - 14}" ry="7" fill="${grain}"/>`;
};
const ear = (x, y, a) => `<ellipse cx="${x}" cy="${y}" rx="2.6" ry="6" transform="rotate(${a} ${x} ${y})"/>`;
export const hero = () => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 232" role="img" aria-label="Grain sacks at a mandi beside a price board with a rising price line">
<ellipse cx="180" cy="202" rx="172" ry="9" fill="#efe6d2"/>
<rect x="238" y="126" width="7" height="74" fill="#7c5a32"/><rect x="312" y="126" width="7" height="74" fill="#7c5a32"/>
<rect x="208" y="20" width="142" height="110" rx="9" fill="#14532d" stroke="#0d3b20" stroke-width="4"/>
<g stroke="#1f6b3a" stroke-width="1.5"><line x1="222" y1="60" x2="336" y2="60"/><line x1="222" y1="84" x2="336" y2="84"/><line x1="222" y1="108" x2="336" y2="108"/></g>
<text x="222" y="48" ${F} font-size="22" font-weight="800" fill="#fde68a">₹</text>
<text x="242" y="45" ${F} font-size="12" fill="#bbf7d0">per quintal</text>
<polyline points="224,110 252,96 276,102 302,74 334,54" fill="none" stroke="#f59f00" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="334" cy="54" r="5" fill="#fde68a"/>
${sack(52, 76, 96, '#e3b448')}${sack(124, 70, 78, '#b8642e')}${sack(184, 50, 56, '#e9d79c')}
<path d="M14 198V120" stroke="#c99a2e" stroke-width="2"/>
<g fill="#e3b448"><ellipse cx="14" cy="114" rx="3" ry="7"/>${ear(9, 128, -35)}${ear(19, 128, 35)}${ear(9, 141, -35)}${ear(19, 141, 35)}${ear(9, 154, -35)}${ear(19, 154, 35)}</g>
</svg>`;
