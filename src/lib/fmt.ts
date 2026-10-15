/** Indian number format, e.g. 452500 -> "4,52,500" */
export const inr = (n: number | null | undefined) => (n == null ? '—' : Math.round(n).toLocaleString('en-IN'));
/** Rs per quintal -> Rs per kg */
export const perKg = (q: number | null | undefined) => (q == null ? '—' : (q / 100).toFixed(2));
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTHS_HI = ['जनवरी', 'फरवरी', 'मार्च', 'अप्रैल', 'मई', 'जून', 'जुलाई', 'अगस्त', 'सितंबर', 'अक्टूबर', 'नवंबर', 'दिसंबर'];
export const dateEn = (iso: string) => { const [y, m, d] = iso.split('-').map(Number); return `${d} ${MONTHS[m - 1]} ${y}`; };
export const dateHi = (iso: string) => { const [y, m, d] = iso.split('-').map(Number); return `${d} ${MONTHS_HI[m - 1]} ${y}`; };
export const change = (now: number, prev: number | null | undefined) => {
  if (prev == null || !prev) return null;
  const diff = now - prev;
  return { diff, pct: (diff / prev) * 100 };
};
