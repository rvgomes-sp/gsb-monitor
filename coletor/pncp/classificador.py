"""Classificador de OBRA v2 — evidência-driven, validado contra golden set.

Corpus de regressão: config/corpus_regressao_obra.json (12 editais reais).
Regras discriminantes (governanca/CORPUS_REGRESSAO_OBRA.md):
  1. design+build ('contratação integrada' / 'projeto E posterior construção') -> OBRA
  2. 'elaboração de projeto' ISOLADO (sem execução/construção) -> NEGATIVO_PROJETO_SEM_EXECUCAO
  3. 'aquisição de material...' -> NEGATIVO_MATERIAL
  4. manutenção de praças/parques/jardinagem, consultoria/serviço técnico -> NEGATIVO_SERVICO
  5. manutenção predial/corretiva de bens imóveis -> LIMITROFE
  6. verbo de execução física + objeto físico -> POSITIVO_OBRA
  7. serviços de engenharia a executar (não só projeto) -> POSITIVO_ENGENHARIA_EXECUTIVA

Empírico (assinatura de itens): catálogo/NCM = 0% no tier >10MM, então usamos
materialOuServico + unidadeMedida + descricao/objeto. Sinais de item reforçam o objeto.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# ---------- rótulos do corpus (nível objeto) ----------
POSITIVO_OBRA = "POSITIVO_OBRA"
POSITIVO_ENGENHARIA_EXECUTIVA = "POSITIVO_ENGENHARIA_EXECUTIVA"
NEGATIVO_MATERIAL = "NEGATIVO_MATERIAL"
NEGATIVO_SERVICO = "NEGATIVO_SERVICO"
NEGATIVO_PROJETO_SEM_EXECUCAO = "NEGATIVO_PROJETO_SEM_EXECUCAO"
LIMITROFE = "LIMITROFE"
INDETERMINADO = "INDETERMINADO"

# ---------- classes de produção (nível contratação) ----------
OBRA_FORTE = "OBRA_FORTE"
REVISAR = "REVISAR"
NAO_OBRA = "NAO_OBRA"

# verbos de obra AUTOSSUFICIENTES: a atividade JÁ É obra, sem precisar de objeto extra
OBRA_NUCLEO_VERBOS = ["constru", "pavimenta", "recapea", "asfalt", "terraplan", "terraplen",
                      "drenagem", "saneamento", "urbaniza", "edifica", "dragagem", "canaliza",
                      "adutora", "barragem", "calcamento"]
# verbos de execução física que precisam de objeto físico/engenharia/empreitada p/ virar obra
EXEC_FRACA = ["reforma", "revitaliza", "recupera", "requalifica", "duplica", "implanta",
              "ampliacao", "restaura", "reparos", "correcoes", "adequacao", "adaptacao",
              "manutencao predial"]
EXEC_FISICA = OBRA_NUCLEO_VERBOS + EXEC_FRACA
# objetos físicos / infraestrutura
OBJ_FISICO = ["rodovia", "estrada", "ponte", "viaduto", "predi", "edifi", "escola",
              "habitacional", "unidade habit", "mercado", "vestiario", "galeria", "ubs",
              "unidade de saude", "quadra", "infraestrutura", "imovel", "saneamento",
              "esgoto", "adutora", "barragem", "praca", "calcamento", "muro", "cobertura",
              "ginasio", "creche", "hospital", "km", "obra"]
# manutenção-serviço (negativo)
MANUT_SERVICO = ["praca", "parque", "area verde", "jardinagem", "paisagismo", "poda",
                 "roçada", "rocada", "limpeza urbana", "capina", "cemiterio", "vias publicas"]
# consultoria/serviço não-obra (negativo)
SERVICO_NEG = ["consultoria", "assessoria", "apoio tecnico", "servico tecnico", "hst",
               "horas de servico", "fabrica de software", "desenvolvimento de sistema",
               "locacao de", "vigilancia", "limpeza e conservacao", "seguranca",
               "recepcao", "portaria", "telefonia", "call center", "outsourcing",
               "gerenciamento de obra", "fiscalizacao de obra", "supervisao de obra",
               "gestao de obra", "apoio a fiscalizacao", "fiscalizacao e supervisao"]
# manutenção predial (limítrofe)
MANUT_PREDIAL = ["predial", "bens imoveis", "imoveis", "corretiva", "preventiva",
                 "infraestrutura predial", "predios"]
# serviços "duros" cujo objeto-NÚCLEO nunca é obra, mesmo que citem manutenção incidental
HARD_SERVICO = ["alimentacao escolar", "merenda", "generos aliment", "nutric", "refeic",
                "alimentacao", "transporte escolar", "limpeza urbana", "coleta de residuo",
                "coleta de lixo", "vigilancia", "seguranca patrimonial", "portaria",
                "brigada", "call center", "telemarketing", "mao de obra terceiriz"]
# verbos que caracterizam ATIVIDADE de obra (para distinguir de simples fornecimento de produto)
ATIVIDADE_OBRA = ["pavimenta", "recapea", "execucao", "construcao", "construir", "reforma",
                  "obra", "terraplan", "drenagem", "edifica", "implanta", "restaura", "recupera"]
# empreitada / execução completa: a CONTRATADA fornece material E mão de obra para
# EXECUTAR o objeto (positivo de obra). NÃO confundir com 'aquisição de material'
# (o órgão comprando material = negativo). Reforça obra quando há verbo de execução.
MARC_EMPREITADA = ["fornecimento de materia", "materia e mao de obra", "materiais e mao de obra",
                   "mao de obra e materia", "mao de obra e os materia", "empreitada",
                   "insumos e mao de obra", "material e mao de obra"]
# unidades estruturais de obra
UNIDADES_OBRA = ["km", "quilometro", "m2", "metro quadrado", "m3", "metro cubico",
                 "metro linear", "metro", "ml", "hectare", "ha", "global", "empreitada", "verba"]
# semântica de obra em item
TERMOS_OBRA = EXEC_FISICA + ["obra", "engenharia", "rodovia", "ponte", "drenagem"]


def _fold(v) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(v or "")) if unicodedata.category(c) != "Mn")
    return s.casefold().strip()


def _tem(t: str, termos) -> bool:
    return any(x in t for x in termos)


# ============ NÍVEL OBJETO (texto) — testado pelo golden set ============
def classificar_objeto(texto: str) -> tuple[str, str]:
    """Retorna (classe_corpus, motivo) a partir do objeto/descrição textual."""
    t = _fold(texto)
    if not t:
        return INDETERMINADO, "objeto vazio"

    exec_fisica = _tem(t, EXEC_FISICA)
    # 'obra' como substantivo (obra rodoviária/obra de...), excluindo 'mão de obra'
    obra_nucleo = len(re.findall(r"\bobra", t)) > t.count("mao de obra")
    empreitada = _tem(t, MARC_EMPREITADA)   # contratada fornece material+mão de obra p/ executar
    tem_projeto = ("projeto" in t) and ("elabora" in t or "projeto basico" in t
                                        or "projeto executivo" in t or "anteprojeto" in t)
    integrada = ("integrad" in t) or ("posterior" in t and exec_fisica) \
        or (tem_projeto and _tem(t, ["constru", "execucao da obra", "edifica"]))

    # 1) design+build: projeto + construção/execução, ou contratação integrada
    if integrada:
        return POSITIVO_OBRA, "design+build (contratação integrada / projeto + construção)"

    # 2) projeto ISOLADO (sem execução física) -> negativo
    if tem_projeto and not exec_fisica:
        return NEGATIVO_PROJETO_SEM_EXECUCAO, "elaboração de projeto sem execução/construção"

    # 3) aquisição de material -> negativo (verbo de COMPRA pelo órgão).
    #    Ressalva: 'fornecimento de materiais e mão de obra' é a CONTRATADA executando -> NÃO é compra.
    if _tem(t, ["aquisic", "compra de"]) and "materia" in t and not empreitada:
        return NEGATIVO_MATERIAL, "aquisição de material (verbo de compra pelo órgão)"

    # 3b) serviços DUROS não-obra (alimentação, limpeza, vigilância, transporte...) -> serviço.
    #     Objeto-núcleo domina manutenção/execução incidental de equipamentos.
    if _tem(t, HARD_SERVICO):
        return NEGATIVO_SERVICO, "serviço não-obra (alimentação/limpeza/vigilância/transporte)"

    # 3c) FORNECIMENTO/aquisição de PRODUTO (sem empreitada, sem atividade de obra) -> material.
    #     Pega 'fornecimento de cimento asfáltico' (o 'asfalt' é adjetivo do produto, não a obra).
    supply = _tem(t, ["fornecimento de", "aquisic", "compra de", "propostas para fornecimento",
                      "aquisicao de", "registro de precos para fornecimento"])
    if supply and not empreitada and not _tem(t, ATIVIDADE_OBRA):
        return NEGATIVO_MATERIAL, "fornecimento/aquisição de produto (sem execução de obra)"

    # 4) manutenção de praças/parques ou consultoria/serviço técnico -> negativo
    if "manuten" in t and _tem(t, MANUT_SERVICO):
        return NEGATIVO_SERVICO, "manutenção de praças/parques/áreas verdes = serviço"
    if _tem(t, SERVICO_NEG) and not exec_fisica:
        return NEGATIVO_SERVICO, "consultoria/serviço técnico (não obra)"

    # 5) manutenção predial/corretiva -> limítrofe
    if "manuten" in t and _tem(t, MANUT_PREDIAL):
        return LIMITROFE, "manutenção predial/corretiva de bens imóveis (obra-adjacente)"

    # 6) verbo de obra AUTOSSUFICIENTE (pavimentação, terraplenagem, construção...) -> obra
    if _tem(t, OBRA_NUCLEO_VERBOS):
        return POSITIVO_OBRA, "verbo de obra autossuficiente (pavimentação/terraplenagem/construção...)"
    # 6b) execução física (fraca) + objeto físico/engenharia/empreitada -> obra
    if exec_fisica and _tem(t, OBJ_FISICO):
        return POSITIVO_OBRA, "verbo de execução física + objeto físico/infraestrutura"
    if exec_fisica and "engenharia" in t:
        return POSITIVO_OBRA, "execução física + engenharia"
    if exec_fisica and empreitada:
        return POSITIVO_OBRA, "execução física + fornecimento de materiais e mão de obra (empreitada)"
    if obra_nucleo and (_tem(t, OBJ_FISICO) or empreitada or "engenharia" in t):
        return POSITIVO_OBRA, "substantivo 'obra' + objeto físico/empreitada/engenharia"

    # 7) serviços de engenharia a executar (não só projeto)
    if "engenharia" in t and _tem(t, ["realizad", "executad", "execucao", "a serem realiz"]):
        return POSITIVO_ENGENHARIA_EXECUTIVA, "serviços de engenharia com execução"
    if "engenharia" in t and not tem_projeto:
        return POSITIVO_ENGENHARIA_EXECUTIVA, "serviços de engenharia (sem marca de projeto isolado)"

    return INDETERMINADO, "sem sinal claro de obra"


# ============ NÍVEL ITEM ============
@dataclass
class SinalItem:
    numero_item: int | None
    a_servico: bool
    b_unidade: bool
    c_semantica: bool

    @property
    def forte(self) -> bool:
        return self.a_servico and self.b_unidade and self.c_semantica

    @property
    def parcial(self) -> bool:
        return self.a_servico and (self.b_unidade or self.c_semantica)


def _unidade_obra(u) -> bool:
    f = _fold(u)
    return any(re.search(rf"\b{re.escape(x)}\b", f) or f == x for x in UNIDADES_OBRA)


def sinal_item(it: dict) -> SinalItem:
    return SinalItem(
        numero_item=it.get("numeroItem"),
        a_servico=(it.get("materialOuServico") or "").upper().startswith("S"),
        b_unidade=_unidade_obra(it.get("unidadeMedida")),
        c_semantica=_tem(_fold(it.get("descricao")), TERMOS_OBRA),
    )


# ============ NÍVEL CONTRATAÇÃO (produção) ============
@dataclass
class Classificacao:
    classe: str                 # OBRA_FORTE | REVISAR | NAO_OBRA
    classe_objeto: str          # rótulo do corpus (auditoria)
    itens_obra: list[int]
    motivo: str


def classificar_contratacao(itens: list[dict], objeto_compra: str = "") -> Classificacao:
    obj_classe, obj_motivo = classificar_objeto(objeto_compra)
    sinais = [sinal_item(it) for it in (itens or [])]
    fortes = [s.numero_item for s in sinais if s.forte]
    parciais = [s.numero_item for s in sinais if s.parcial]

    # negativos do objeto DOMINAM (definem a natureza da compra)
    if obj_classe in (NEGATIVO_MATERIAL, NEGATIVO_SERVICO, NEGATIVO_PROJETO_SEM_EXECUCAO):
        return Classificacao(NAO_OBRA, obj_classe, [], obj_motivo)
    # obra confirmada por objeto ou por sinal forte de item
    if obj_classe == POSITIVO_OBRA or fortes:
        return Classificacao(OBRA_FORTE, obj_classe or "item_forte",
                             fortes or [s.numero_item for s in sinais if s.c_semantica],
                             f"{obj_motivo}" + (f" | {len(fortes)} item(ns) A∧B∧C" if fortes else ""))
    # engenharia executiva, limítrofe, ou sinal parcial -> revisar (drill)
    if obj_classe in (POSITIVO_ENGENHARIA_EXECUTIVA, LIMITROFE) or parciais:
        return Classificacao(REVISAR, obj_classe, parciais, obj_motivo)
    return Classificacao(NAO_OBRA, obj_classe, [], obj_motivo)
