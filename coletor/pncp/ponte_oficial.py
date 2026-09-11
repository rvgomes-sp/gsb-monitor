"""Item identity after factual events. No economic or textual selection."""
import json
from urllib.parse import urlencode
from evt007_catalog_bridge import Catser,ITEM_ENDPOINT,exact_integer,item_key,utcnow,IDENTITY_COLUMNS

VERSION="003-S-02-R-ETAPA3-v1"
def resolve(event,cli,catser):
    case,n=event["case_id"],event["item_number"]
    it=event["item"]
    out=dict.fromkeys(IDENTITY_COLUMNS)
    out.update(item_key=item_key(case,n),case_id=case,item_number=n,
        id_contratacao_pncp=case,bridge_version=VERSION,
        catalog_match_status="AQUISICAO_IDENTIDADE_FALHOU",
        identity_source="PNCP_ITENS",identity_endpoint=event["item_endpoint"],
        identity_payload={"pncp_item":it},raw_field_presence={})
    def validate(row):
        for name in ("numeroControlePNCP","numeroControlePNCPCompra","idContratacaoPNCP"):
            if row.get(name) not in (None,"",case): raise ValueError("conflicting "+name)
        for name in ("numeroItem","numeroItemPncp"):
            if row.get(name) is not None and exact_integer(row[name])!=str(n): raise ValueError("conflicting "+name)
    try:
        validate(it);validate(event["procurement"])
        source=it
        # NULL is preserved; an absent code field authorizes the certified complement route.
        if "codItemCatalogo" not in it:
            params={"tipo":"numeroControlePNCPCompra","codigo":case}
            if it.get("idCompra"):
                if type(it["idCompra"]) is not str: raise ValueError("invalid idCompra")
                params={"tipo":"idCompra","codigo":it["idCompra"]}
            if it.get("idCompraItem"):
                if type(it["idCompraItem"]) is not str: raise ValueError("invalid idCompraItem")
                params["idCompraItem"]=it["idCompraItem"]
            url=ITEM_ENDPOINT+"?"+urlencode(params)
            out["identity_endpoint"]=url;out["identity_source"]="PNCP_ITENS+COMPRASGOV"
            payload=cli.get(url,endpoint="identidade")
            out["identity_payload"]["comprasgov_response"]=payload
            if not isinstance(payload,dict) or not isinstance(payload.get("resultado"),list):
                raise ValueError("invalid identity response")
            if payload.get("totalPaginas",1) not in (None,0,1): raise ValueError("identity pagination incomplete")
            matches=[]
            for row in payload["resultado"]:
                if not isinstance(row,dict): raise ValueError("invalid identity row")
                rid=row.get("idContratacaoPNCP") or row.get("numeroControlePNCPCompra")
                if rid==case and exact_integer(row.get("numeroItemPncp"))==str(n): matches.append(row)
            if len(matches)!=1: raise ValueError("item multiplicity: "+str(len(matches)))
            source=matches[0];validate(source)
            for name in ("idCompra","idCompraItem"):
                if it.get(name) is not None and source.get(name)!=it[name]: raise ValueError("conflicting "+name)
            if "materialOuServico" in it and source.get("materialOuServico")!=it["materialOuServico"]:
                raise ValueError("conflicting materialOuServico")
        # Hash refers to actual raw response acquired by the canonical client.
        evidence=next((e for e in reversed(cli.evidencias) if e.url==out["identity_endpoint"]),None)
        if evidence is None: raise ValueError("raw response evidence unavailable")
        out["identity_payload_hash"]=evidence.source_hash
        out["identity_acquired_at"]=utcnow()
        m=it["materialOuServico"] if "materialOuServico" in it else source.get("materialOuServico")
        code=source.get("codItemCatalogo")
        out.update(material_ou_servico_raw=m,cod_item_catalogo_raw=code,
            raw_field_presence={"materialOuServico": "materialOuServico" in it or "materialOuServico" in source,
                                "codItemCatalogo":"codItemCatalogo" in source},
            id_compra=source.get("idCompra"),id_compra_item=source.get("idCompraItem"))
        if m not in ("M","S"):
            out["catalog_match_status"]="NAMESPACE_NAO_RESOLVIDO";return out
        out["catalog_namespace"]="CATMAT" if m=="M" else "CATSER"
        if m=="M":
            out["catalog_match_status"]="MATERIAL_PRESERVADO"
            if code not in (None,""):
                try: out["catalog_code"]=exact_integer(code)
                except ValueError: out["failure_reason"]="noncanonical material code; raw preserved"
            return out
        if code in (None,""):
            out["catalog_match_status"]="CODIGO_CATALOGO_AUSENTE";return out
        out["catalog_code"]=exact_integer(code)
    except Exception as exc:
        out["failure_reason"]=str(exc);return out
    try:
        match=catser.lookup(code)
        out.update(catalog_snapshot_sha256=catser.observed_hash,
            catalog_match_status="CATSER_MATCH_EXATO" if match else "CATSER_NAO_LOCALIZADO")
        if match: out.update(catalog_name=match["nomeServico"],catalog_group_code=match["codigoGrupo"],catalog_group_name=match["nomeGrupo"])
    except Exception as exc:
        out.update(catalog_match_status="ERRO_TECNICO_CATALOGO",failure_reason=str(exc),catalog_snapshot_sha256=catser.observed_hash)
    return out

def map_fact(event):
    rr=event["result"];proc=event["procurement"]
    seq=rr.get("sequencialResultado");ni=rr.get("niFornecedor")
    if type(seq) is not int or seq<0 or not isinstance(ni,str) or not ni:
        raise ValueError("missing/noncanonical result sequence or supplier identifier")
    # Collision-free tuple; every component is explicitly present in the official source.
    key=json.dumps([event["case_id"],event["item_number"],seq,ni],ensure_ascii=False,separators=(",",":"))
    fields=dict(result_key=key,case_id=event["case_id"],item_number=event["item_number"],
        result_sequence=seq,supplier_identifier=ni,supplier_name=rr.get("nomeRazaoSocialFornecedor"),
        supplier_size_id=rr.get("porteFornecedorId"),supplier_size_name=rr.get("porteFornecedorNome"),
        legal_nature_id=rr.get("naturezaJuridicaId"),legal_nature_name=rr.get("naturezaJuridicaNome"),
        result_date=rr["dataResultado"],inclusion_at=rr["dataInclusao"],
        update_at=rr.get("dataAtualizacao"),cancellation_at=rr.get("dataCancelamento"),
        homologated_quantity=rr.get("quantidadeHomologada"),homologated_unit_value=rr.get("valorUnitarioHomologado"),
        homologated_total_value=rr.get("valorTotalHomologado"),platform=proc.get("usuarioNome"),
        platform_delta_status=event["freshness_class"],source_name="PNCP_INTEGRACAO_10.17",
        source_payload=json.dumps(rr,ensure_ascii=False),delta_calendar_days=event["delta_calendar_days"],
        delta_business_days=event["delta_business_days"],freshness_class=event["freshness_class"])
    return fields

def run_bridge(events,cli,catser):
    grouped={}
    for e in events: grouped.setdefault(item_key(e["case_id"],e["item_number"]),[]).append(e)
    identities=[]
    for rows in grouped.values():
        out=resolve(rows[0],cli,catser)
        if any(r["item"]!=rows[0]["item"] for r in rows):
            out.update(catalog_match_status="AQUISICAO_IDENTIDADE_FALHOU",failure_reason="conflicting PNCP item observations")
        identities.append(out)
    return identities
