"""Legacy compatibility: catalog identity is uncertified; no prefix lookup.

The old item-code -> class/group prefix assumptions were disproved in Gate A.2.
The call surface fails closed until a certified adapter is reviewed.
"""
from dataclasses import dataclass

PENDENTE = "PENDENTE"


@dataclass
class Familia:
    codigo: str | None
    nome: str | None
    status: str
    origem: str


class Classificador:
    def __init__(self, caminho=None):
        self.caminho = caminho  # compatibility only; no unvalidated catalog read

    def classificar(self, item: dict) -> Familia:
        return Familia(None, None, PENDENTE, "identidade_catalogo_nao_certificada")

    def eh_obra(self, item: dict) -> bool:
        return False
