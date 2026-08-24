import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const portalRoot = resolve(import.meta.dirname, "..");
const monitorRoot = resolve(portalRoot, "..");

function readPortal(path) {
  return readFileSync(resolve(portalRoot, path), "utf8");
}

function readMonitor(path) {
  return readFileSync(resolve(monitorRoot, path));
}

function sha256(path) {
  return createHash("sha256").update(readMonitor(path)).digest("hex").toUpperCase();
}

test("os dois perfis institucionais permanecem identificados corretamente", () => {
  const auth = readPortal("lib/auth.ts");
  assert.match(auth, /name:\s*"Rodrigo Vazquez"/);
  assert.match(auth, /role:\s*"Diretor do Projeto"/);
  assert.match(auth, /initials:\s*"RV"/);
  assert.match(auth, /name:\s*"Ana Fonseca"/);
  assert.match(auth, /role:\s*"Diretora Institucional"/);
});

test("a autoria operacional usa o usuário autenticado", () => {
  const client = readPortal("public/assets/vip_monitor.js");
  assert.match(client, /operator:\s*authenticatedPortalUser\?\.name/);
  assert.doesNotMatch(
    client,
    /data:\s*\{\s*\.\.\.data,\s*operator:\s*"Ana Fonseca"/,
  );
});

test("as rotas D1/R2 e as entradas de sincronização estão presentes", () => {
  for (const path of [
    "app/api/feed/route.ts",
    "app/api/operations/route.ts",
    "app/api/document-reading/route.ts",
    "app/api/document/route.ts",
    "app/api/documents/route.ts",
    "app/api/outreach/route.ts",
    "app/api/proposals/route.ts",
    "app/api/import/snapshot/route.ts",
    "app/api/import/document/route.ts",
  ]) {
    const source = readPortal(path);
    assert.doesNotMatch(source, /proxyToSites/);
  }
  const snapshot = readPortal("app/api/import/snapshot/route.ts");
  assert.match(snapshot, /document_jobs/);
  const operations = readPortal("app/api/operations/route.ts");
  assert.match(operations, /document_jobs/);
});

test("as regras e os motores-base continuam byte a byte preservados", () => {
  const baseline = {
    "config/comercial/regras_comerciais.json":
      "432A716C6F45A96FAF3574558EE4A81462CD3CB21F9058C7E97C99717E7EAD02",
    "config/documentos/documentos_evt007.json":
      "EA0C4F3B2EB57B22CEEA37A04B0F3682997224BADAAF28198ABF7BF84DA98702",
    "config/documentos/regras_garantia.json":
      "EC0365F0259FA66EABFC50529925C230746B96A47F2E413508C6CAFAA8392C1D",
    "src/processar_documentos_evt007.py":
      "22F56CE96CB127C3826C012B600C180411472C464146B0C5C44CB66B43895A6F",
    "src/Descobrir_EVT007_D1.ps1":
      "F4523E4DD7C11DA91CE4E1E110B9667610461C1E6D7AC735FF2E95015739E198",
    "src/Consolidar_EVT007_DadosAbertos.ps1":
      "61811AC75DE13CB6BBEC6BFB62A52A51590DC4A38B4BAF9738B1C72316E514E8",
  };
  for (const [path, digest] of Object.entries(baseline)) {
    assert.equal(sha256(path), digest, path);
  }
});

test("a ponte local continua apontando para as rotas de importação preservadas", () => {
  const sync = readMonitor("src/sincronizar_monitor_nuvem.py").toString("utf8");
  assert.match(sync, /\/api\/import\/snapshot/);
  assert.match(sync, /\/api\/import\/document/);
  assert.match(sync, /x-import-token/);
});

test("as rotas sensíveis exigem sessão autenticada (fail-closed)", () => {
  const guardedRoutes = [
    "app/api/feed/route.ts",
    "app/api/operations/route.ts",
    "app/api/document-reading/route.ts",
    "app/api/document/route.ts",
    "app/api/documents/route.ts",
    "app/api/outreach/route.ts",
    "app/api/proposals/route.ts",
  ];
  for (const path of guardedRoutes) {
    const source = readPortal(path);
    assert.match(
      source,
      /requireAuthenticatedSession/,
      `${path} deve chamar requireAuthenticatedSession`,
    );
    assert.match(
      source,
      /if\s*\(!guard\.ok\)\s*return\s+guard\.response/,
      `${path} deve interromper a execução quando o guard falhar`,
    );
  }
  const guard = readPortal("lib/require-session.ts");
  assert.match(guard, /PORTAL_AUTH_SECRET/);
  assert.match(guard, /status:\s*503/);
  assert.match(guard, /status:\s*401/);
});

test("as rotas de importação continuam guardadas apenas por IMPORT_TOKEN", () => {
  for (const path of [
    "app/api/import/snapshot/route.ts",
    "app/api/import/document/route.ts",
  ]) {
    const source = readPortal(path);
    assert.match(source, /IMPORT_TOKEN/);
    assert.match(source, /x-import-token/);
    assert.doesNotMatch(
      source,
      /requireAuthenticatedSession/,
      `${path} não deve depender de sessão de portal — a ponte local usa IMPORT_TOKEN`,
    );
  }
});
