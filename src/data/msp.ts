// Minimum Support Prices (₹ per quintal), Government of India, CCEA decisions:
//  Kharif marketing season 2026-27: approved 13 May 2026.  Rabi marketing season 2027-28: approved 30 Sep 2026.
// Cross-checked against several reports of the PIB releases (16 Nov 2026). Update when the next decisions come out
// (kharif ~May-June, rabi ~Sep-Oct).
export type MspRow = { crop: string; hindi: string; prev: number; now: number; slug?: string; margin?: number };

export const KHARIF = { season: '2026-27', prevSeason: '2025-26', approved: '13 May 2026', rows: [
  { crop: 'Paddy (Common)', hindi: 'धान (सामान्य)', prev: 2369, now: 2441, slug: 'paddy' },
  { crop: 'Paddy (Grade A)', hindi: 'धान (ग्रेड ए)', prev: 2389, now: 2461 },
  { crop: 'Jowar (Hybrid)', hindi: 'ज्वार (हाइब्रिड)', prev: 3699, now: 4023 },
  { crop: 'Jowar (Maldandi)', hindi: 'ज्वार (मालदंडी)', prev: 3749, now: 4073 },
  { crop: 'Bajra', hindi: 'बाजरा', prev: 2775, now: 2900, slug: 'bajra' },
  { crop: 'Ragi', hindi: 'रागी', prev: 4886, now: 5205 },
  { crop: 'Maize', hindi: 'मक्का', prev: 2400, now: 2410, slug: 'maize' },
  { crop: 'Tur / Arhar', hindi: 'तुअर / अरहर', prev: 8000, now: 8450 },
  { crop: 'Moong', hindi: 'मूंग', prev: 8768, now: 8780, slug: 'moong' },
  { crop: 'Urad', hindi: 'उड़द', prev: 7800, now: 8200 },
  { crop: 'Groundnut', hindi: 'मूंगफली', prev: 7263, now: 7517, slug: 'groundnut' },
  { crop: 'Sunflower seed', hindi: 'सूरजमुखी', prev: 7721, now: 8343 },
  { crop: 'Soybean (Yellow)', hindi: 'सोयाबीन (पीला)', prev: 5328, now: 5708, slug: 'soyabean' },
  { crop: 'Sesamum', hindi: 'तिल', prev: 9846, now: 10346 },
  { crop: 'Nigerseed', hindi: 'रामतिल', prev: 9537, now: 10052 },
  { crop: 'Cotton (Medium Staple)', hindi: 'कपास (मध्यम रेशा)', prev: 7710, now: 8267, slug: 'cotton' },
  { crop: 'Cotton (Long Staple)', hindi: 'कपास (लंबा रेशा)', prev: 8110, now: 8667 },
] as MspRow[] };

export const RABI = { season: '2027-28', prevSeason: '2026-27', approved: '30 September 2026', rows: [
  { crop: 'Wheat', hindi: 'गेहूं', prev: 2585, now: 2610, slug: 'wheat', margin: 106 },
  { crop: 'Barley', hindi: 'जौ', prev: 2150, now: 2286, margin: 58 },
  { crop: 'Gram (Chana)', hindi: 'चना', prev: 5875, now: 5958, slug: 'chana', margin: 59 },
  { crop: 'Lentil (Masur)', hindi: 'मसूर', prev: 7000, now: 7390, margin: 92 },
  { crop: 'Rapeseed & Mustard', hindi: 'सरसों', prev: 6200, now: 6613, slug: 'mustard', margin: 96 },
  { crop: 'Safflower', hindi: 'कुसुम', prev: 6540, now: 7215, margin: 50 },
] as MspRow[] };

/** The MSP that applies to grain being sold in mandis now (Nov 2026): kharif 2026-27 for kharif crops; for rabi crops
 *  the 2026-27 marketing season rate (prev) is the one in force until the new rabi harvest is marketed from April 2027. */
export function mspFor(slug: string) {
  const k = KHARIF.rows.find((r) => r.slug === slug);
  if (k) return { msp: k.now, season: `Kharif ${KHARIF.season}`, next: null as null | { msp: number; season: string }, row: k };
  const r = RABI.rows.find((x) => x.slug === slug);
  if (r) return { msp: r.prev, season: `Rabi ${RABI.prevSeason}`, next: { msp: r.now, season: `Rabi ${RABI.season} (from April 2027)` }, row: r };
  return null;
}
