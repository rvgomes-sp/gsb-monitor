import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  assertCommercialCase,
  calculateGuaranteeStack,
  observedPortfolioTotal,
  sortApproachMap,
} from "../public/assets/commercial_intelligence.mjs";

const payload = JSON.parse(
  await readFile(
    new URL("../public/data/commercial_intelligence_cases.json", import.meta.url),
    "utf8",
  ),
);
const etam = payload.cases["04892707000291-1-000011/2025"];

function almostEqual(actual, expected, tolerance = 0.01) {
  assert.ok(
    Math.abs(actual - expected) <= tolerance,
    `esperado ${expected}, recebido ${actual}`,
  );
}

test("ETAM mantém a divergência documental e não presume limite", () => {
  assert.equal(assertCommercialCase(etam), true);
  assert.equal(etam.limitStatus, "NAO_VERIFICADO");
  assert.ok(etam.flags.includes("DIVERGENCIA_DOCUMENTAL"));
});

test("motor calcula os cenários nominais de 10%, 15% e 20%", () => {
  const result = calculateGuaranteeStack(etam.guarantee);
  almostEqual(result.executionAmount, 32913305.39686);
  almostEqual(result.minimumNominalCapacity, 49369958.09529);
  almostEqual(result.maximumNominalCapacity, 65826610.79372);
  assert.equal(result.minimumTotalPercent, 15);
  assert.equal(result.maximumTotalPercent, 20);
});

test("adicional do art. 59 não incide no caso ETAM", () => {
  const result = calculateGuaranteeStack(etam.guarantee);
  assert.ok(etam.guarantee.proposalValue > result.article59Threshold);
  assert.equal(result.article59Additional, 0);
});

test("carteira pública observada soma sete contratos sem se declarar backlog", () => {
  assert.equal(etam.portfolio.contracts.length, 7);
  almostEqual(observedPortfolioTotal(etam.portfolio.contracts), 535551850.16);
  assert.equal(etam.portfolio.backlogStatus, "NAO_CONFIRMADO");
});

test("mapa de abordagem começa por Administrativo e Financeiro", () => {
  const contacts = sortApproachMap(etam.approachMap);
  assert.equal(contacts[0].priority, 1);
  assert.match(contacts[0].area, /Administrativa e Financeira/);
});

test("painel expõe o botão e o modal de dossiê", async () => {
  const [html, script] = await Promise.all([
    readFile(new URL("../public/monitor_vip.html", import.meta.url), "utf8"),
    readFile(new URL("../public/assets/vip_monitor.js", import.meta.url), "utf8"),
  ]);
  assert.match(html, /commercial-intelligence-modal/);
  assert.match(script, /data-commercial-intelligence/);
  assert.match(script, /Carteira contratada observada/);
});

test("atalhos preservam o enquadramento horizontal", async () => {
  const script = await readFile(
    new URL("../public/assets/vip_monitor.js", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(script, /href="#opportunities-section"/);
  assert.match(script, /data-queue-route=/);
  assert.match(script, /window\.scrollTo\(\{ top: Math\.max\(0, top\), left: 0/);
  assert.match(script, /normalizeLegacyOpportunityHash/);
});
