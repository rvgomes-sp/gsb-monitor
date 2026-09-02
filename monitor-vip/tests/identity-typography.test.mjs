import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');
const css = read('../public/assets/identity_typography.css');

test('duas telas carregam apenas a fonte aprovada e o override por último', () => {
  for (const page of ['investigacao_evt007', 'carteira_ana']) {
    const html = read(`../public/${page}.html`);
    assert.match(html, /family=Cormorant\+Garamond:ital,wght@0,500;0,600;1,400/);
    assert.match(html, /referrerpolicy="no-referrer"/);
    assert.ok(html.indexOf('identity_typography.css') > html.indexOf(`assets/${page}.css`));
    assert.doesNotMatch(html, /EB\+Garamond|Libre\+Baskerville/);
  }
});

test('tipografia separa display e números operacionais sem reabrir layout', () => {
  assert.match(css, /--font-brand: 'Cormorant Garamond', serif/);
  assert.match(css, /--font-operational-number: 'Segoe UI', sans-serif/);
  assert.match(css, /tabular-nums/);
  assert.doesNotMatch(css, /Georgia|Times New Roman|Libre Baskerville|EB Garamond/);
  assert.doesNotMatch(css, /(?:^|[;{])\s*(?:display|grid-template[^:]*|gap|height|width|overflow|visibility)\s*:/m);
});

test('monograma mantém proposta de marca, Cormorant 600 e halo contido', () => {
  assert.match(css, /\.brand-seal > span[\s\S]*?font-weight: 600/);
  assert.match(css, /transform: translate\(-1px, 1px\)/);
  assert.match(css, /0 0 18px 0 #d18d5d33/);
  assert.match(css, /0 0 20px 0 #df9aa333/);
});
