import hashlib,json
from typing import Protocol
from .contracts import TransportEvidence, ReasonCode

class Transport(Protocol):
    def fetch_item(self, case_id:str, item_number:int)->TransportEvidence: ...

def sha256_bytes(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def verify_and_parse(e:TransportEvidence):
    if e.error:
        return None,ReasonCode.ERRO_TRANSPORTE
    if sha256_bytes(e.payload_raw)!=e.payload_sha256:
        return None,ReasonCode.HASH_DIVERGENTE
    try:
        parsed=json.loads(e.payload_raw.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError):
        return None,ReasonCode.ERRO_PARSE
    if parsed!=e.payload:
        return None,ReasonCode.HASH_DIVERGENTE
    return parsed,None
