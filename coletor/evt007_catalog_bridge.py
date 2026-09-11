"""003-S/02-R. Official item identity; no commercial decision or monitor sink."""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import time
import urllib.request
from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode

try:
    from . import evt007_collect_comprasgov as collector
except ImportError:
    import evt007_collect_comprasgov as collector

VERSION = "003-S-02-R-v1"
TARGET = "2026-09-09"
MONITOR_WRITE = False
CATSER_HASH = "f3cd884220115be97fd7782a25e799d8c64390786794d27c3fef53806e67f264"
ITEM_ENDPOINT = ("https://dadosabertos.compras.gov.br/modulo-contratacoes/"
                 "2.1_consultarItensContratacoes_PNCP_14133_Id")
STATES = ("CATSER_MATCH_EXATO", "CATSER_NAO_LOCALIZADO", "MATERIAL_PRESERVADO",
          "CODIGO_CATALOGO_AUSENTE", "NAMESPACE_NAO_RESOLVIDO",
          "AQUISICAO_IDENTIDADE_FALHOU", "ERRO_TECNICO_CATALOGO")


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def exact_integer(value):
    """Only JSON integers or canonical decimal CSV/text representations; no aliases."""
    if type(value) is int and value >= 0:
        return str(value)
    if type(value) is str and value and all(c in "0123456789" for c in value):
        if str(int(value)) == value:
            return value
    raise ValueError("noncanonical integer")


def item_key(case_id, item_number):
    if not isinstance(case_id, str) or not case_id or case_id != case_id.strip():
        raise ValueError("missing or nonliteral case_id")
    number = exact_integer(item_number)
    if int(number) < 1:
        raise ValueError("invalid item_number")
    return json.dumps([case_id, int(number)], ensure_ascii=False, separators=(",", ":"))


class EvidenceHTTP:
    """One bounded request per item. Preserve received bytes before interpreting them."""
    def __init__(self, directory, timeout=30):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.calls = 0

    def __call__(self, url):
        self.calls += 1
        stem = self.directory / f"request_{self.calls:05d}"
        meta = {"url": url, "started_at": utcnow(), "status": "STARTED"}
        write_json(stem.with_suffix(".json"), meta)
        try:
            request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "GSB-Curador/003-S-02-R"})
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                stem.with_suffix(".body").write_bytes(body)
                meta.update(http_status=response.status, headers=dict(response.headers), bytes=len(body), sha256=sha256(body).hexdigest())
                if response.status != 200:
                    raise ValueError("unexpected HTTP status")
            payload = json.loads(body.decode("utf-8-sig"))
            meta["status"] = "RECEIVED"
            return payload, meta
        except Exception as exc:
            meta.update(status="FAILED", error_type=type(exc).__name__, error=str(exc))
            raise
        finally:
            meta["finished_at"] = utcnow()
            write_json(stem.with_suffix(".json"), meta)


class Catser:
    def __init__(self, path):
        self.path = Path(path)
        self.rows = None
        self.observed_hash = None
        self.error = None
        self.lookups = 0

    def load(self):
        if self.error:
            raise ValueError(self.error)
        if self.rows is not None:
            return
        try:
            body = self.path.read_bytes()
            self.observed_hash = sha256(body).hexdigest()
            if self.observed_hash != CATSER_HASH:
                raise ValueError("CATSER SHA-256 mismatch")
            reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")), delimiter=";", strict=True)
            required = {"codigoServico", "nomeServico", "codigoGrupo", "nomeGrupo"}
            if not required <= set(reader.fieldnames or []):
                raise ValueError("CATSER schema mismatch")
            index = {}
            for row in reader:
                if None in row or any(row.get(k) is None for k in required):
                    raise ValueError("malformed CATSER row")
                code = exact_integer(row["codigoServico"])
                if code in index:
                    raise ValueError("duplicate CATSER key")
                index[code] = row
            self.rows = index
        except Exception as exc:
            self.error = str(exc)
            raise

    def lookup(self, code):
        self.load()
        code = exact_integer(code)
        self.lookups += 1
        return self.rows.get(code)


def select_results(results):
    selected = []
    for row in results:
        value = row.get("homologated_total_value")
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            raise ValueError("invalid economic value")
        amount = Decimal(str(value))
        if not amount.is_finite():
            raise ValueError("nonfinite economic value")
        if amount > Decimal("10000000"):
            selected.append(row)
    return selected


def result_identifiers(row):
    raw = row["source_payload"]
    raw = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(raw, dict):
        raise ValueError("source_payload is not an object")
    case = row["case_id"]
    number = int(exact_integer(row["item_number"]))
    item_key(case, number)
    for field in ("idContratacaoPNCP", "numeroControlePNCPCompra"):
        if raw.get(field) not in (None, "", case):
            raise ValueError("conflicting official procurement identifiers")
    if int(exact_integer(raw.get("numeroItemPncp"))) != number:
        raise ValueError("conflicting official item number")
    return {"id_contratacao_pncp": case, "id_compra": raw.get("idCompra"), "id_compra_item": raw.get("idCompraItem")}


def acquire_identity(rows, http, catser):
    first = rows[0]
    identity = dict(item_key=item_key(first["case_id"], first["item_number"]),
                    case_id=first["case_id"], item_number=first["item_number"],
                    bridge_version=VERSION, catalog_match_status="AQUISICAO_IDENTIDADE_FALHOU",
                    identity_source=collector.SOURCE, identity_endpoint=None,
                    identity_payload_hash=None, identity_acquired_at=None,
                    material_ou_servico_raw=None, cod_item_catalogo_raw=None,
                    catalog_namespace=None, catalog_code=None, catalog_name=None,
                    catalog_group_code=None, catalog_group_name=None,
                    catalog_snapshot_sha256=None, identity_payload=None,
                    raw_field_presence={}, failure_reason=None)
    try:
        identifiers = [result_identifiers(row) for row in rows]
        for name in ("id_contratacao_pncp", "id_compra", "id_compra_item"):
            values = [ids[name] for ids in identifiers if ids[name] not in (None, "")]
            if any(type(v) is not str for v in values) or len(set(values)) > 1:
                raise ValueError(f"conflicting or non-string {name}")
            identity[name] = values[0] if values else None
        # Both enum routes are documented. Never manufacture an idCompra/idCompraItem.
        params = {"tipo": "numeroControlePNCPCompra", "codigo": identity["case_id"]}
        if identity["id_compra"]:
            params = {"tipo": "idCompra", "codigo": identity["id_compra"]}
        if identity["id_compra_item"]:
            params["idCompraItem"] = identity["id_compra_item"]
        url = ITEM_ENDPOINT + "?" + urlencode(params)
        identity["identity_endpoint"] = url
        payload, meta = http(url)
        identity.update(identity_payload_hash=meta["sha256"], identity_payload=payload,
                        identity_acquired_at=meta.get("finished_at") or utcnow())
        if not isinstance(payload, dict) or not isinstance(payload.get("resultado"), list):
            raise ValueError("unexpected item response schema")
        if payload.get("totalPaginas", 1) not in (None, 0, 1):
            raise ValueError("item response incomplete: multiple pages")
        matches = []
        for item in payload["resultado"]:
            if not isinstance(item, dict):
                raise ValueError("malformed item observation")
            case = item.get("idContratacaoPNCP") or item.get("numeroControlePNCPCompra")
            if case == identity["case_id"] and exact_integer(item.get("numeroItemPncp")) == str(identity["item_number"]):
                matches.append(item)
        if len(matches) != 1:
            raise ValueError(f"item observation multiplicity: {len(matches)}; no deduplication rule")
        item = matches[0]
        for field in ("idContratacaoPNCP", "numeroControlePNCPCompra"):
            if item.get(field) not in (None, "", identity["case_id"]):
                raise ValueError("conflicting procurement identifiers in item response")
        for raw_name, name in (("idCompra", "id_compra"), ("idCompraItem", "id_compra_item")):
            if identity[name] is not None and item.get(raw_name) != identity[name]:
                raise ValueError(f"official identifier mismatch: {raw_name}")
            if item.get(raw_name) is not None:
                if type(item[raw_name]) is not str:
                    raise ValueError(f"non-string identifier: {raw_name}")
                identity[name] = item[raw_name]
        material, code = item.get("materialOuServico"), item.get("codItemCatalogo")
        identity.update(material_ou_servico_raw=material, cod_item_catalogo_raw=code,
                        raw_field_presence={k: k in item for k in ("materialOuServico", "codItemCatalogo")})
        if material not in ("S", "M"):
            identity["catalog_match_status"] = "NAMESPACE_NAO_RESOLVIDO"
            return identity
        identity["catalog_namespace"] = "CATSER" if material == "S" else "CATMAT"
        if material == "M":
            identity["catalog_match_status"] = "MATERIAL_PRESERVADO"
            if code not in (None, ""):
                try:
                    identity["catalog_code"] = exact_integer(code)
                except ValueError:
                    identity["failure_reason"] = "noncanonical material code; raw preserved"
            return identity
        if code is None or code == "":
            identity["catalog_match_status"] = "CODIGO_CATALOGO_AUSENTE"
            return identity
        identity["catalog_code"] = exact_integer(code)
    except Exception as exc:
        identity["failure_reason"] = str(exc)
        return identity
    try:
        match = catser.lookup(code)
        identity["catalog_snapshot_sha256"] = catser.observed_hash
        identity["catalog_match_status"] = "CATSER_MATCH_EXATO" if match else "CATSER_NAO_LOCALIZADO"
        if match:
            identity.update(catalog_name=match["nomeServico"], catalog_group_code=match["codigoGrupo"], catalog_group_name=match["nomeGrupo"])
    except Exception as exc:
        identity.update(catalog_match_status="ERRO_TECNICO_CATALOGO", failure_reason=str(exc), catalog_snapshot_sha256=catser.observed_hash)
    return identity


def bridge(results, http, catser):
    selected = select_results(results)
    grouped = {}
    # Invalid administrative keys stop the batch instead of fabricating identities.
    for row in selected:
        key = item_key(row.get("case_id"), row.get("item_number"))
        grouped.setdefault(key, []).append(row)
    identities = [acquire_identity(rows, http, catser) for rows in grouped.values()]
    index = {row["item_key"]: row for row in identities}
    audit = [{**{k: row.get(k) for k in ("result_key", "case_id", "item_number", "result_sequence", "supplier_identifier", "supplier_name", "homologated_total_value")},
              **index[item_key(row["case_id"], row["item_number"]) ]} for row in selected]
    return selected, identities, audit


def metrics(results, selected, identities, calls):
    acquired = [i for i in identities if i["catalog_match_status"] != "AQUISICAO_IDENTIDADE_FALHOU"]
    services = [i for i in acquired if i["material_ou_servico_raw"] == "S"]
    with_code = [i for i in services if i["cod_item_catalogo_raw"] not in (None, "")]
    m = dict(TOTAL_RESULTADOS_COLETADOS=len(results), TOTAL_RESULTADOS_ACIMA_10M=len(selected),
             TOTAL_ITENS_UNICOS_ACIMA_10M=len(identities), TOTAL_IDENTIDADES_ADQUIRIDAS=len(acquired),
             TOTAL_AQUISICAO_FALHOU=len(identities)-len(acquired), N_S=len(services),
             N_M=sum(i["material_ou_servico_raw"] == "M" for i in acquired),
             N_NAMESPACE_NAO_RESOLVIDO=sum(i["catalog_match_status"] == "NAMESPACE_NAO_RESOLVIDO" for i in identities),
             N_S_COM_CODIGO=len(with_code), N_S_SEM_CODIGO=len(services)-len(with_code),
             CHAMADAS_DE_IDENTIDADE_REALIZADAS=calls)
    for state in ("CATSER_MATCH_EXATO", "CATSER_NAO_LOCALIZADO", "MATERIAL_PRESERVADO", "ERRO_TECNICO_CATALOGO"):
        m["N_"+state] = sum(i["catalog_match_status"] == state for i in identities)
    def rate(n, d):
        return n/d if d else None
    eligible = len(with_code)-m["N_ERRO_TECNICO_CATALOGO"]
    m.update(taxa_aquisicao_identidade=rate(len(acquired), len(identities)),
             taxa_codigo_entre_servicos=rate(len(with_code), len(services)),
             taxa_match_catser=rate(m["N_CATSER_MATCH_EXATO"], eligible),
             denominador_match_sem_falha_tecnica=eligible)
    return m


RESULT_COLUMNS = ("result_key", "case_id", "item_number", "result_sequence", "supplier_identifier",
                  "supplier_name", "supplier_size_id", "supplier_size_name", "legal_nature_id",
                  "legal_nature_name", "result_date", "inclusion_at", "update_at", "cancellation_at",
                  "homologated_quantity", "homologated_unit_value", "homologated_total_value",
                  "platform", "platform_delta_status", "source_name", "source_payload")
IDENTITY_COLUMNS = ("item_key", "case_id", "item_number", "id_contratacao_pncp", "id_compra", "id_compra_item",
                    "material_ou_servico_raw", "cod_item_catalogo_raw", "catalog_namespace", "catalog_code",
                    "catalog_match_status", "catalog_name", "catalog_group_code", "catalog_group_name",
                    "identity_source", "identity_endpoint", "identity_payload_hash", "identity_acquired_at",
                    "catalog_snapshot_sha256", "bridge_version", "identity_payload", "raw_field_presence", "failure_reason")


def persist(conn, results, identities, run_id):
    """Caller supplies transaction. INSERT only: preserve first observations and raw facts."""
    for row in results:
        cols = RESULT_COLUMNS
        conn.execute(f"INSERT INTO gsb.evt007_results ({','.join(cols)}) VALUES ({','.join('%('+c+')s' for c in cols)}) ON CONFLICT (result_key) DO NOTHING", row)
    for row in identities:
        params = dict(row)
        for c in ("material_ou_servico_raw", "cod_item_catalogo_raw", "identity_payload", "raw_field_presence"):
            params[c] = json.dumps(params.get(c), ensure_ascii=False)
        cols = IDENTITY_COLUMNS
        conn.execute(f"INSERT INTO gsb.evt007_item_identity ({','.join(cols)}) VALUES ({','.join('%('+c+')s' for c in cols)}) ON CONFLICT (item_key) DO NOTHING", params)
        # Each run remains queryable even when an earlier identity already exists.
        conn.execute("INSERT INTO gsb.evt007_item_identity_observations (run_id,item_key,observation) VALUES (%s,%s,%s::jsonb) ON CONFLICT (run_id,item_key) DO NOTHING",
                     (run_id, row["item_key"], json.dumps(row, ensure_ascii=False)))


def preflight(conn):
    required = ("gsb.evt007_results", "gsb.evt007_item_identity", "gsb.evt007_item_identity_observations")
    for name in required:
        if conn.execute("SELECT to_regclass(%s)", (name,)).fetchone()[0] is None:
            raise RuntimeError("missing canonical relation: " + name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", choices=[TARGET], required=True)
    parser.add_argument("--catser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--persist", action="store_true")
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {"order":"003-S/02-R", "date":args.date, "bridge_version":VERSION,
              "monitor_write":False, "status":"STARTED", "started_at":utcnow(), "metrics":None,
              "persisted":False}
    conn = None
    try:
        if args.persist:
            import psycopg
            conn = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=20)
            preflight(conn)
        factual_http = EvidenceHTTP(args.output / "factual_http")
        results, collection = collector.collect(date.fromisoformat(args.date), 0, lambda url: factual_http(url)[0])
        report["collection"] = collection
        write_json(args.output / "factual_results.json", results)
        if collection["status"] != "COMPLETE":
            raise RuntimeError("incomplete factual batch")
        identity_http = EvidenceHTTP(args.output / "identity_http")
        catser = Catser(args.catser)
        selected, identities, audit = bridge(results, identity_http, catser)
        report["metrics"] = metrics(results, selected, identities, identity_http.calls)
        report["catser_sha256_observed"] = catser.observed_hash
        write_json(args.output / "identities.json", identities)
        write_json(args.output / "audit.json", audit)
        fields = ["result_key", "case_id", "item_number", "result_sequence", "supplier_identifier",
                  "supplier_name", "homologated_total_value", "material_ou_servico_raw",
                  "cod_item_catalogo_raw", "catalog_namespace", "catalog_code", "catalog_name",
                  "catalog_match_status", "identity_payload_hash", "failure_reason"]
        with (args.output / "audit.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(audit)
        if conn:
            with conn.transaction():
                persist(conn, results, identities, args.output.name)
            conn.commit()
            report["persisted"] = True
        report["status"] = "PROCESSED" if not catser.error else "ERRO_TECNICO_CATALOGO"
        return 0 if not catser.error else 2
    except Exception as exc:
        report.update(status="EXECUCAO_BLOQUEADA", error_type=type(exc).__name__, error=str(exc))
        return 2
    finally:
        if conn:
            conn.close()
        report.update(TEMPO_TOTAL=time.monotonic()-started, finished_at=utcnow())
        write_json(args.output / "execution.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
