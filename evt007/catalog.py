"""Catalog contract only. No certified identity mapping exists in Gate B."""
from .contracts import CATALOG_STATES

CERTIFIED_CATALOG_SYSTEMS = frozenset()  # A future evidence-backed code change, not an env toggle.


def catalog_contract(item: dict) -> dict:
    cat = item.get("catalogo")
    cat = cat if isinstance(cat, dict) else {}
    code = item.get("catalogoCodigoItem")
    return {
        "catalogo_id_raw": cat.get("id", item.get("catalogoId")),
        "catalogo_nome_raw": cat.get("nome"), "catalogo_codigo_item_raw": code,
        "material_ou_servico_raw": item.get("materialOuServico"),
        "catalogo_objeto_raw": item.get("catalogo"), "categoria_item_catalogo_raw": item.get("categoriaItemCatalogo"),
        "catalogo_sistema": "NAO_IDENTIFICADO", "catalogo_codigo_item": None,
        "catalogo_validacao_status": "NAO_FORNECIDO" if code in (None, "") else "NAO_VALIDADO",
        "codigo_oficial": None, "nome_oficial": None, "classe_oficial": None, "grupo_oficial": None,
        "catalogo_snapshot_data": None, "catalogo_snapshot_sha256": None,
        "gsb_curadoria_status_raw": None, "gsb_ativo_motor_raw": None,
        "gsb_ativo_motor": None, "gsb_curadoria_versao": None, "gsb_curadoria_fonte": None,
        "bloqueio": "IDENTIDADE_PNCP_CATALOGO_NAO_CERTIFICADA",
    }


def validate_catalog_state(value: str) -> str:
    if value not in CATALOG_STATES:
        raise ValueError("invalid catalog validation state")
    return value


def retain_legacy_curation(row: dict, version: str, source: str) -> dict:
    """Raw False remains historical False; it does NOT mean explicit deactivation."""
    return {"gsb_curadoria_status_raw": row.get("gsbStatus"),
            "gsb_ativo_motor_raw": row.get("gsbAtivoMotor"),
            "gsb_ativo_motor": None, "gsb_curadoria_versao": version,
            "gsb_curadoria_fonte": source, "curadoria_payload_raw": dict(row),
            "transposicao_status": "AGUARDA_DECISAO_SEMANTICA"}
