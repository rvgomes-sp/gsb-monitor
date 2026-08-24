import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("production source identifies the GSB Monitor", async () => {
  const [page, html, script] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../public/monitor_vip.html", import.meta.url), "utf8"),
    readFile(new URL("../public/assets/vip_monitor.js", import.meta.url), "utf8"),
  ]);
  assert.match(page, /monitor_vip\.html/);
  assert.match(html, /VIP \| GSB Monitor/);
  assert.match(html, /opportunity-pagination/);
  assert.match(script, /api\/outreach/);
  assert.match(script, /api\/proposals/);
  assert.match(script, /opportunityPageSize/);
  assert.match(script, /LOCAL_FALLBACK/);
});
