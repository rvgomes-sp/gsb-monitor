"""Normalize individual results; never sum items or invent a missing identity."""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlsplit
from dataclasses import dataclass, field
from .contracts import SOURCE, MODALITIES, FLOOR, calendar_day, digest, integer, money


def check_enrichment_origin(enrichment, identity):
    url = urlsplit(str(enrichment.get("source_url") or ""))
    if url.scheme != "https" or url.username or url.password:
        raise ValueError("invalid enrichment origin")
    if enrichment.get("source") == "PNCP_ITENS":
        process = identity["process_id"]
        cnpj, rest = process.split("-1-")
        seq, year = rest.split("/")
        base = f"/api/pncp/v1/orgaos/{cnpj}/compras/{year}/{int(seq)}"
        if url.netloc != "pncp.gov.br" or url.path != base + f"/itens/{identity['numero_item']}":
            raise ValueError("PNCP item origin mismatch")
        purchase = enrichment.get("purchase")
        if purchase:
            purchase_url = urlsplit(str(enrichment.get("purchase_source_url") or ""))
            if (purchase_url.scheme, purchase_url.netloc, purchase_url.path) != ("https", "pncp.gov.br", base):
                raise ValueError("purchase origin required separately")
    else:
        # No alternate discovery source. Compras.gov enrichment adapter remains
        # unimplemented until its item/purchase mapping is separately verified.
        raise ValueError("enrichment adapter not certified")


def process_reference(value) -> str:
    text = str(value or "").strip()
    match = re.fullmatch(r"([0-9]{14})-1-([0-9]+)/([0-9]{4})", text)
    if not match or int(match[2]) < 1:
        raise ValueError("invalid PNCP process reference")
    return f"{match[1]}-1-{int(match[2]):06d}/{match[3]}"


def supplier_reference(value) -> str:
    # Formatting normalization, not a new business filter or check-digit claim.
    text = re.sub(r"[. /-]", "", str(value or "").strip()).upper()
    if not re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}|[0-9]{11}", text):
        raise ValueError("supplier identity insufficient")
    return text


@dataclass
class Fact:
    event_id: str | None
    identity: dict | None
    raw: dict
    raw_hash: str
    normalized: dict = field(default_factory=dict)
    status: str = "QUARENTENA"
    reasons: list[str] = field(default_factory=list)
    enrichment: dict | None = None


def normalize_result(raw: dict, window: str, enrichment: dict | None = None) -> Fact:
    """Enrichment is an item-scoped, source-labelled preserved envelope, not discovery.

    envelope = {process_id, numeroItem, source, source_url, item, purchase}
    Its content hash is recorded. No provider is queried here.
    """
    calendar_day(window)
    fact = Fact(None, None, raw, digest(raw))
    try:
        refs = [process_reference(raw[k]) for k in ("numeroControlePNCPCompra", "idContratacaoPNCP") if raw.get(k)]
        if not refs or len(set(refs)) != 1:
            raise ValueError("absent/conflicting process identity")
        identity = {"namespace": SOURCE + ":PNCP_RESULTADO", "process_id": refs[0],
                    "numero_item": integer(raw.get("numeroItemPncp")),
                    "sequencial_resultado": integer(raw.get("sequencialResultado"))}
        fact.identity = identity
        fact.event_id = "evt007:" + digest(identity)
    except (ValueError, TypeError):
        fact.reasons.append("IDENTIDADE_INSUFICIENTE_OU_CONTRADITORIA")
        return fact

    norm = fact.normalized
    try:
        norm["supplier_id"] = supplier_reference(raw.get("niFornecedor"))
    except ValueError:
        fact.reasons.append("FORNECEDOR_NAO_IDENTIFICADO")
    norm["supplier_name"] = raw.get("nomeRazaoSocialFornecedor")
    # Source field name is dataResultadoPncp; business concept is dataResultado.
    try:
        norm["query_date"] = calendar_day(raw.get("dataResultadoPncp"))
        norm["dataResultado"] = norm["query_date"]
        norm["dataResultado_source_field"] = "dataResultadoPncp"
        if raw.get("dataResultado") is not None and calendar_day(raw["dataResultado"]) != norm["dataResultado"]:
            fact.reasons.append("RELOGIOS_RESULTADO_CONTRADITORIOS")
        if norm["query_date"] != window:
            fact.reasons.append("FORA_JANELA_RESULTADO")
    except (TypeError, ValueError):
        fact.reasons.append("DATA_RESULTADO_INVALIDA")
    norm["dataInclusao_raw"] = raw.get("dataInclusaoPncp")
    norm["dataAtualizacao_raw"] = raw.get("dataAtualizacaoPncp")
    # Inclusion is latency evidence only, never event identity or eligibility clock.
    try:
        norm["latencia_dias_calendario"] = (
            date.fromisoformat(calendar_day(raw.get("dataInclusaoPncp")))
            - date.fromisoformat(norm["dataResultado"])).days
    except (ValueError, KeyError, TypeError):
        norm["latencia_dias_calendario"] = None

    cancelled = any(raw.get(k) not in (None, "") for k in ("dataCancelamentoPncp", "motivoCancelamento"))
    try:
        situation = integer(raw.get("situacaoCompraItemResultadoId"))
    except ValueError:
        situation = None
    norm["situacao_resultado"] = situation
    if cancelled or situation == 2:
        fact.reasons.append("RESULTADO_CANCELADO")
    elif situation != 1:
        fact.reasons.append("HOMOLOGACAO_NAO_CONFIRMADA")
    name = raw.get("situacaoCompraItemResultadoNome")
    if situation == 1 and name is not None and str(name).strip().casefold() != "informado":
        fact.reasons.append("SITUACAO_CONTRADITORIA")
    try:
        total = money(raw.get("valorTotalHomologado"))
        norm["valor_homologado_individual"] = str(total)
        if total <= FLOOR:
            fact.reasons.append("VALOR_NAO_SUPERIOR_A_10MM")
    except ValueError:
        fact.reasons.append("VALOR_INDIVIDUAL_INVALIDO")

    purchase, item = {}, {}
    if enrichment is not None:
        try:
            if (process_reference(enrichment.get("process_id")) != identity["process_id"]
                    or integer(enrichment.get("numeroItem")) != identity["numero_item"]
                    or enrichment.get("source") not in (SOURCE, "PNCP_ITENS")
                    or not enrichment.get("source_url")):
                raise ValueError("enrichment scope mismatch")
            item, purchase = enrichment.get("item", {}), enrichment.get("purchase", {})
            if not isinstance(item, dict) or not isinstance(purchase, dict):
                raise ValueError("invalid enrichment payload")
            if integer(item.get("numeroItem")) != identity["numero_item"]:
                raise ValueError("item mismatch")
            check_enrichment_origin(enrichment, identity)
            purchase_ref = purchase.get("numeroControlePNCP")
            if purchase_ref and process_reference(purchase_ref) != identity["process_id"]:
                raise ValueError("purchase mismatch")
            fact.enrichment = enrichment
            norm["enrichment_sha256"] = digest(enrichment)
        except (ValueError, TypeError):
            item, purchase = {}, {}
            fact.reasons.append("ENRIQUECIMENTO_INCOMPATIVEL")
    modality_values = [v for v in (raw.get("modalidadeId"), purchase.get("modalidadeId")) if v is not None]
    try:
        modalities = {integer(v) for v in modality_values}
        if len(modalities) != 1:
            raise ValueError("absent/conflicting modality")
        norm["modalidade"] = modalities.pop()
        if norm["modalidade"] not in MODALITIES:
            fact.reasons.append("MODALIDADE_FORA_DO_CONTRATO")
    except ValueError:
        fact.reasons.append("MODALIDADE_AUSENTE_OU_CONTRADITORIA")
    norm["descricao_item"] = item.get("descricao")
    norm["objeto_contexto"] = purchase.get("objetoCompra")
    norm["item_raw"] = item
    exclusions = {"RESULTADO_CANCELADO", "VALOR_NAO_SUPERIOR_A_10MM", "MODALIDADE_FORA_DO_CONTRATO", "FORA_JANELA_RESULTADO"}
    fact.status = "INELEGIVEL" if exclusions.intersection(fact.reasons) else "QUARENTENA" if fact.reasons else "ELEGIVEL"
    return fact
