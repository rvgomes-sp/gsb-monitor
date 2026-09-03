import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const path = new URL('../../monitor-vip/app/api/import/snapshot/route.ts', import.meta.url);
const source = readFileSync(path, 'utf8');
// Type erasure for this dependency-free handler; do not import/build the app.
const { POST } = await import('data:text/javascript;base64,' + Buffer.from(source.replace('request: Request', 'request')).toString('base64'));

test('retired route rejects unauthenticated requests', async () => {
  const original = process.env.IMPORT_TOKEN;
  try {
    process.env.IMPORT_TOKEN = 'synthetic-unit-token';
    const result = await POST(new Request('http://localhost/api/import/snapshot', { method: 'POST' }));
    assert.equal(result.status, 401);
  } finally {
    if (original === undefined) delete process.env.IMPORT_TOKEN; else process.env.IMPORT_TOKEN = original;
  }
});

test('authorized legacy call returns 410 without parsing payload or database access', async () => {
  const original = process.env.IMPORT_TOKEN;
  try {
    process.env.IMPORT_TOKEN = 'synthetic-unit-token';
    const request = { headers: new Headers({ 'x-import-token': 'synthetic-unit-token' }),
      json: () => { throw new Error('must never read an import payload'); } };
    const result = await POST(request);
    assert.equal(result.status, 410);
    assert.equal((await result.json()).operational_writes, 0);
    assert.doesNotMatch(source, /getSql|ensureDatabase|DELETE FROM|INSERT INTO/);
  } finally {
    if (original === undefined) delete process.env.IMPORT_TOKEN; else process.env.IMPORT_TOKEN = original;
  }
});
