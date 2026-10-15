// Text -> SVG <path> using HarfBuzz shaping (correct Hindi conjuncts and vowel signs).
// resvg's own text shaping mangles some Devanagari words, so card text is drawn as outlines.
import { Blob, Face, Font, Buffer, Variation, shape } from 'harfbuzzjs';
import { readFileSync } from 'node:fs';

export function loadFont(file) {
  const face = new Face(new Blob(readFileSync(file)));
  const fonts = {};
  const get = (weight) => {
    if (!fonts[weight]) {
      const f = new Font(face);
      f.setVariations([new Variation('wght', weight)]);
      fonts[weight] = f;
    }
    return fonts[weight];
  };
  return { upem: face.upem, get };
}

/** Returns { d, width } in pixels for `text` at `size`, baseline at y=0, starting at x=0. */
export function textPath(font, text, size, weight = 400) {
  const f = font.get(weight);
  const buf = new Buffer();
  buf.addText(text);
  buf.guessSegmentProperties();
  shape(f, buf);
  const scale = size / font.upem;
  let x = 0;
  const parts = [];
  for (const g of buf.getGlyphInfosAndPositions()) {
    const path = f.glyphToPath(g.codepoint);
    if (path) {
      const ox = (x + (g.xOffset || 0)) * scale;
      const oy = -(g.yOffset || 0) * scale;
      // glyph outlines are y-up in font units: flip and scale into SVG space
      parts.push(`<path transform="translate(${ox.toFixed(2)} ${oy.toFixed(2)}) scale(${scale.toFixed(5)} ${(-scale).toFixed(5)})" d="${path}"/>`);
    }
    x += g.xAdvance || 0;
  }
  return { svg: parts.join(''), width: x * scale };
}

/** Positioned text: anchor 'start' | 'end'. */
export function drawText(font, text, x, y, size, { weight = 400, fill = '#000', anchor = 'start' } = {}) {
  const { svg, width } = textPath(font, text, size, weight);
  const left = anchor === 'end' ? x - width : x;
  return `<g transform="translate(${left.toFixed(2)} ${y})" fill="${fill}">${svg}</g>`;
}
