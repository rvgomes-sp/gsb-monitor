from dataclasses import dataclass
from typing import Any
from .evidence import sha256_bytes
from .contracts import ReasonCode

@dataclass
class CatalogSnapshot:
    namespace:str
    raw:bytes
    expected_sha256:str
    rows:list[dict[str,Any]]
    code_field:str="code"
    name_field:str="name"
    group_code_field:str="group_code"
    group_name_field:str="group_name"
    scope:str="SNAPSHOT_ONLY"
    lookups:int=0

    @property
    def sha256(self): return sha256_bytes(self.raw)

    def index(self):
        if self.sha256!=self.expected_sha256:
            raise CatalogError(ReasonCode.SNAPSHOT_HASH_DIVERGENTE)
        out={}
        for row in self.rows:
            code=row.get(self.code_field)
            if type(code) not in (str,int) or isinstance(code,bool) or str(code)=="":
                raise CatalogError(ReasonCode.CAMPO_RAW_INVALIDO)
            code=str(code)
            if code in out: raise CatalogError(ReasonCode.CHAVE_DUPLICADA_CATALOGO)
            out[code]=row
        return out

    def lookup(self,code:str):
        idx=self.index();self.lookups+=1
        return idx.get(code)

class CatalogError(RuntimeError):
    def __init__(self,reason): self.reason=reason;super().__init__(reason.value)
