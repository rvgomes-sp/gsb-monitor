from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class MicStatus(str, Enum):
    MATCH_EXATO_CATMAT="MATCH_EXATO_CATMAT"
    MATCH_EXATO_CATSER="MATCH_EXATO_CATSER"
    CODIGO_AUSENTE="CODIGO_AUSENTE"
    NAMESPACE_NAO_COMPROVADO="NAMESPACE_NAO_COMPROVADO"
    CODIGO_OFICIAL_NAO_LOCALIZADO="CODIGO_OFICIAL_NAO_LOCALIZADO"
    IDENTIDADE_NAO_RESOLVIDA="IDENTIDADE_NAO_RESOLVIDA"
    ERRO_TECNICO="ERRO_TECNICO"

class ReasonCode(str, Enum):
    CONFLITO_IDENTIFICADORES="CONFLITO_IDENTIFICADORES"
    MULTIPLICIDADE_ITEM="MULTIPLICIDADE_ITEM"
    EVIDENCIA_INSUFICIENTE="EVIDENCIA_INSUFICIENTE"
    HASH_DIVERGENTE="HASH_DIVERGENTE"
    SNAPSHOT_INDISPONIVEL="SNAPSHOT_INDISPONIVEL"
    SNAPSHOT_HASH_DIVERGENTE="SNAPSHOT_HASH_DIVERGENTE"
    SNAPSHOT_NAMESPACE_DIVERGENTE="SNAPSHOT_NAMESPACE_DIVERGENTE"
    CHAVE_DUPLICADA_CATALOGO="CHAVE_DUPLICADA_CATALOGO"
    CAMPO_RAW_INVALIDO="CAMPO_RAW_INVALIDO"
    ESCOPO_NAMESPACE_NAO_COMPROVADO="ESCOPO_NAMESPACE_NAO_COMPROVADO"
    ERRO_PARSE="ERRO_PARSE"
    ERRO_TRANSPORTE="ERRO_TRANSPORTE"

@dataclass(frozen=True)
class FactualResult:
    result_key:str
    case_id:str
    item_number:int
    source_name:str
    source_payload:dict[str,Any]=field(default_factory=dict)

@dataclass(frozen=True)
class TransportEvidence:
    url:str
    http_status:int|None
    payload_raw:bytes
    payload_sha256:str
    payload:Any
    started_at:str
    finished_at:str
    error:str|None=None

@dataclass
class MicObservation:
    item_key:str
    case_id:str
    item_number:int
    source_result_keys:list[str]
    source_name:str
    mic_status:MicStatus
    mic_reason_code:ReasonCode|None=None
    source_field_name:str|None=None
    material_ou_servico_raw:Any=None
    catalogo_id_raw:Any=None
    catalogo_nome_raw:Any=None
    catalogo_codigo_item_raw:Any=None
    catalog_namespace:str|None=None
    catalog_code:str|None=None
    resolution_method:str="OFFICIAL_ITEM_EXACT"
    namespace_rule_version:str|None=None
    identity_source:str|None=None
    identity_endpoint:str|None=None
    identity_http_status:int|None=None
    identity_payload_raw:bytes|None=None
    identity_payload_sha256:str|None=None
    identity_payload:Any=None
    identity_started_at:str|None=None
    identity_acquired_at:str|None=None
    catalog_snapshot_sha256:str|None=None
    catalog_snapshot_scope:str|None=None
    catalog_name:str|None=None
    catalog_group_code:str|None=None
    catalog_group_name:str|None=None
    failure_reason:str|None=None
