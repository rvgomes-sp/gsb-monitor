import json
from collections import defaultdict
from dataclasses import asdict
from .contracts import FactualResult,MicObservation,MicStatus,ReasonCode
from .evidence import verify_and_parse
from .catalog import CatalogError

def item_key(case_id:str,item_number:int)->str:
    if not isinstance(case_id,str) or not case_id or case_id!=case_id.strip():
        raise ValueError("invalid case_id")
    if type(item_number) is not int or item_number<1: raise ValueError("invalid item_number")
    return json.dumps([case_id,item_number],ensure_ascii=False,separators=(",",":"))

def canonical_code(value):
    if type(value) is int and value>=0: return str(value)
    if isinstance(value,str) and value.isdigit() and str(int(value))==value: return value
    raise ValueError("noncanonical catalog code")

class MicEngine:
    def __init__(self,transport,catalogs,namespace_rule,namespace_rule_version):
        self.transport=transport;self.catalogs=catalogs
        self.namespace_rule=dict(namespace_rule);self.namespace_rule_version=namespace_rule_version

    def run(self,records:list[FactualResult]):
        grouped=defaultdict(list)
        for r in records: grouped[item_key(r.case_id,r.item_number)].append(r)
        return [self._resolve(k,rows) for k,rows in sorted(grouped.items())]

    def _base(self,key,rows):
        first=rows[0]
        return MicObservation(item_key=key,case_id=first.case_id,item_number=first.item_number,
            source_result_keys=sorted({r.result_key for r in rows}),source_name=first.source_name,
            mic_status=MicStatus.IDENTIDADE_NAO_RESOLVIDA,
            namespace_rule_version=self.namespace_rule_version)

    def _resolve(self,key,rows):
        o=self._base(key,rows)
        if len({r.source_name for r in rows})!=1:
            o.mic_reason_code=ReasonCode.CONFLITO_IDENTIFICADORES;o.failure_reason="source_name divergence";return o
        try: ev=self.transport.fetch_item(o.case_id,o.item_number)
        except Exception as exc:
            o.mic_status=MicStatus.ERRO_TECNICO;o.mic_reason_code=ReasonCode.ERRO_TRANSPORTE;o.failure_reason=str(exc);return o
        o.identity_endpoint=ev.url;o.identity_http_status=ev.http_status
        o.identity_payload_raw=ev.payload_raw;o.identity_payload_sha256=ev.payload_sha256
        o.identity_payload=ev.payload;o.identity_started_at=ev.started_at;o.identity_acquired_at=ev.finished_at
        parsed,reason=verify_and_parse(ev)
        if reason:
            o.mic_status=MicStatus.ERRO_TECNICO;o.mic_reason_code=reason;o.failure_reason=ev.error;return o
        o.identity_source="OFFICIAL_ITEM_TRANSPORT"
        observations=parsed.get("resultado") if isinstance(parsed,dict) else None
        if not isinstance(observations,list):
            o.mic_reason_code=ReasonCode.EVIDENCIA_INSUFICIENTE;o.failure_reason="official envelope missing resultado";return o
        matches=[]
        for row in observations:
            if not isinstance(row,dict): continue
            case=row.get("case_id",row.get("idContratacaoPNCP",row.get("numeroControlePNCPCompra")))
            number=row.get("item_number",row.get("numeroItemPncp",row.get("numeroItem")))
            if case==o.case_id and number==o.item_number: matches.append(row)
        if len(matches)!=1:
            o.mic_reason_code=ReasonCode.MULTIPLICIDADE_ITEM if len(matches)>1 else ReasonCode.EVIDENCIA_INSUFICIENTE
            o.failure_reason=f"unambiguous matches: {len(matches)}";return o
        row=matches[0]
        for raw in rows:
            for name in ("idCompra","idCompraItem"):
                expected=raw.source_payload.get(name)
                if expected is not None and row.get(name)!=expected:
                    o.mic_reason_code=ReasonCode.CONFLITO_IDENTIFICADORES;o.failure_reason=f"conflicting {name}";return o
        material=row.get("materialOuServico")
        field=None;code=None
        for name in ("catalogoCodigoItem","codItemCatalogo"):
            if name in row:
                if field is not None:
                    o.mic_reason_code=ReasonCode.CAMPO_RAW_INVALIDO;o.failure_reason="multiple official catalog code fields";return o
                field=name;code=row[name]
        o.source_field_name=field;o.material_ou_servico_raw=material
        o.catalogo_id_raw=row.get("catalogoId");o.catalogo_nome_raw=row.get("catalogoNome")
        o.catalogo_codigo_item_raw=code
        namespace=self.namespace_rule.get(material)
        if namespace not in ("CATMAT","CATSER"):
            o.mic_status=MicStatus.NAMESPACE_NAO_COMPROVADO;o.mic_reason_code=ReasonCode.ESCOPO_NAMESPACE_NAO_COMPROVADO;return o
        o.catalog_namespace=namespace
        if code in (None,""):
            o.mic_status=MicStatus.CODIGO_AUSENTE;return o
        try: o.catalog_code=canonical_code(code)
        except ValueError as exc:
            o.mic_status=MicStatus.IDENTIDADE_NAO_RESOLVIDA;o.mic_reason_code=ReasonCode.CAMPO_RAW_INVALIDO;o.failure_reason=str(exc);return o
        snapshot=self.catalogs.get(namespace)
        if snapshot is None:
            o.mic_status=MicStatus.ERRO_TECNICO;o.mic_reason_code=ReasonCode.SNAPSHOT_INDISPONIVEL;return o
        try: match=snapshot.lookup(o.catalog_code)
        except CatalogError as exc:
            o.mic_status=MicStatus.ERRO_TECNICO;o.mic_reason_code=exc.reason;return o
        o.catalog_snapshot_sha256=snapshot.sha256;o.catalog_snapshot_scope=snapshot.scope
        if not match:
            o.mic_status=MicStatus.CODIGO_OFICIAL_NAO_LOCALIZADO;return o
        o.mic_status=MicStatus.MATCH_EXATO_CATMAT if namespace=="CATMAT" else MicStatus.MATCH_EXATO_CATSER
        o.catalog_name=match.get(snapshot.name_field);o.catalog_group_code=match.get(snapshot.group_code_field)
        o.catalog_group_name=match.get(snapshot.group_name_field)
        return o

def serialize(observations):
    def conv(v): return v.value if hasattr(v,"value") else v
    return [{k:conv(v) for k,v in asdict(o).items()} for o in observations]
