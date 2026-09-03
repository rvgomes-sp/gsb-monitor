"""Conservative obligation grammar, not an ordered family-regex classifier.

Lexing retains source spans. Head actions, coordination, purpose, exclusions and
execution complements are separate roles. Unknown grammar abstains. This is a
bounded deterministic parser, NOT a claim to unrestricted language understanding.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field

VERSION = "obligation-grammar-1"
RULE_VERSION = "gsb-domain-obra-1"


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.casefold()) if unicodedata.category(c) != "Mn")


@dataclass(frozen=True)
class Token:
    word: str
    start: int
    end: int


def lex(text):
    return [Token(fold(m.group()), m.start(), m.end()) for m in re.finditer(r"\w+|[,;:()]", text)]


@dataclass
class Obligation:
    obrigacao_principal: str | None = None
    natureza_contratual: str | None = None
    meios_execucao: list = field(default_factory=list)
    insumos: list = field(default_factory=list)
    obrigacoes_acessorias: list = field(default_factory=list)
    negativas: list = field(default_factory=list)
    limitacoes: list = field(default_factory=list)
    destinacao: list = field(default_factory=list)
    trecho_suporte_obrigacao: str | None = None
    trecho_suporte_natureza: str | None = None
    suporte_spans: list = field(default_factory=list)
    ambiguidade: bool = True
    motivos: list = field(default_factory=list)
    descricao_item_raw: str | None = None
    objeto_contexto_raw: str | None = None
    parser_versao: str = VERSION


# Exact head lexemes, used only in syntactic action positions (not anywhere).
HEADS = {}
for nature, words in {
    "OBRA": "construcao construir pavimentacao pavimentar recapeamento recapar reforma reformar ampliacao ampliar restauracao restaurar recuperacao recuperar implantacao implantar terraplenagem terraplanagem edificacao edificar",
    "FORNECIMENTO": "fornecimento fornecer aquisicao adquirir compra comprar",
    "SERVICO_LIMPEZA_CONSERVACAO": "limpeza limpar conservacao conservar",
    "LOCACAO": "locacao locar aluguel",
    "SERVICO_TECNICO_ENGENHARIA": "elaboracao elaborar projeto projetos fiscalizacao fiscalizar supervisao supervisionar",
    "SERVICO_VIGILANCIA": "vigilancia vigiar",
    "SERVICO_TRANSPORTE": "transporte transportar",
}.items():
    HEADS.update({word: nature for word in words.split()})

WRAPPER = set("contratacao contratar de da do das dos a o as os uma um empresa especializada especializado servicos servico prestacao prestar para destinada destinado visando execucao executar na em area no ramo civil engenharia fornecedora tecnica tecnico responsavel por futura eventual registro precos pelo pela e somente apenas exclusiva exclusivamente".split())
PHYSICAL = set("unidade unidades escola escolas ponte pontes rodovia rodovias estrada estradas predio predios edificacao edificacoes hospital hospitais creche creches quadra quadras viaduto viadutos sede sedes barragem barragens adutora adutoras aeroporto aeroportos porto portos rua ruas avenida avenidas via vias muro muros pavimento pavimentos habitacional habitacionais administrativa administrativas canteiro".split())
OBJECT_MODIFIERS = set("de da do das dos a o as os um uma novo nova novos novas completa completo asfalto asfaltica asfaltico estrutural integral e".split())
MATERIALS = set("materiais material insumos insumo pecas peca consumiveis ferramentas".split())
MEANS = set("equipamentos equipamento veiculos veiculo maquinas maquina motorista motoristas".split())
ACCESSORY = set("vigilancia seguranca transporte limpeza manutencao".split())


def phrase(tokens, words):
    values = [t.word for t in tokens]
    return any(values[i:i + len(words)] == words for i in range(len(values) - len(words) + 1))


def parse_obligation(description: str | None, context: str | None = None) -> Obligation:
    out = Obligation(descricao_item_raw=description, objeto_contexto_raw=context)
    if not isinstance(description, str) or not description.strip():
        out.motivos.append("DESCRICAO_ITEM_AUSENTE")
        return out  # Never classify every item from the global object.
    tokens = lex(description)
    if not tokens:
        out.motivos.append("DESCRICAO_SEM_NUCLEO")
        return out

    def excerpt(start, stop):
        return description[tokens[start].start:tokens[stop - 1].end] if stop > start else ""

    def span(start, stop, role):
        value = excerpt(start, stop)
        out.suporte_spans.append({"inicio": tokens[start].start, "fim": tokens[stop - 1].end,
                                  "texto": value, "papel": role, "fonte": "descricao_item"})
        return value

    # Consume only known procurement wrappers; never seek a convenient keyword
    # beyond an unknown nominal head (e.g. "software para construção...").
    head = 0
    while head < len(tokens) and tokens[head].word not in HEADS:
        if tokens[head].word not in WRAPPER and tokens[head].word not in (",", ":"):
            out.motivos.append("NUCLEO_FORA_DA_GRAMATICA")
            return out
        head += 1
    if head == len(tokens):
        out.motivos.append("NUCLEO_NAO_IDENTIFICADO")
        return out

    # Structural scope boundary. Words in purpose/accessory/exclusion clauses
    # cannot compete with the principal action.
    boundary = len(tokens)
    clause_markers = {"com", "incluindo", "mediante", "sem", "exceto", "excluindo", "para", "visando", ";"}
    for i in range(head + 1, len(tokens)):
        if tokens[i].word in clause_markers:
            boundary = i
            break
    root = tokens[head:boundary]
    principal = span(head, boundary, "obrigacao_principal")
    out.obrigacao_principal = principal
    out.trecho_suporte_obrigacao = principal
    out.trecho_suporte_natureza = principal
    nature = HEADS[tokens[head].word]

    # Coordinate principal actions are all evaluated, never first-match wins.
    coordinated = [HEADS[root[i + 1].word] for i in range(len(root) - 1)
                   if root[i].word in ("e", ",", "ou") and root[i + 1].word in HEADS]
    if any(n != nature for n in coordinated):
        out.motivos.append("OBRIGACOES_PRINCIPAIS_SEM_PREDOMINANCIA")

    if nature == "OBRA":
        target = next((t.word for t in root[1:] if t.word not in OBJECT_MODIFIERS and t.word not in HEADS), None)
        if target not in PHYSICAL:
            out.motivos.append("EXECUCAO_FISICA_NAO_SUSTENTADA")
    if nature == "SERVICO_TECNICO_ENGENHARIA" and not any(t.word in {"projeto", "projetos", "obra", "obras", "engenharia"} for t in root):
        out.motivos.append("SERVICO_TECNICO_SEM_ESCOPO_DE_ENGENHARIA")
    if nature == "FORNECIMENTO" and phrase(root, ["mao", "de", "obra"]):
        nature = "SERVICO_MAO_OBRA"

    starts = [i for i in range(boundary, len(tokens)) if tokens[i].word in clause_markers]
    for j, start in enumerate(starts):
        stop = starts[j + 1] if j + 1 < len(starts) else len(tokens)
        chunk = tokens[start:stop]
        marker = tokens[start].word
        text = span(start, stop, "clausula_" + marker)
        if marker in {"sem", "exceto", "excluindo"}:
            out.negativas.append(text)
            out.limitacoes.append(text)
            if nature == "OBRA" and any(t.word in {"execucao", "construcao", "obra", "obras", "executar"} for t in chunk[1:]):
                out.motivos.append("EXECUCAO_NEGADA_OU_LIMITADA")
        elif marker in {"para", "visando"}:
            out.destinacao.append(text)
            # Project + subsequent execution is not silently re-labelled obra.
            if nature == "SERVICO_TECNICO_ENGENHARIA" and any(t.word == "posterior" for t in chunk):
                out.motivos.append("ESCOPO_INTEGRADO_REQUER_REVISAO")
        elif marker == ";":
            out.motivos.append("MULTIPLOS_ESCOPOS_REQUEREM_REVISAO")
        else:
            if phrase(chunk, ["mao", "de", "obra"]):
                at = next(i for i in range(start, stop - 2) if [t.word for t in tokens[i:i+3]] == ["mao", "de", "obra"])
                out.meios_execucao.append(span(at, at + 3, "meio_execucao"))
            for k in range(start, stop):
                if tokens[k].word in MATERIALS:
                    out.insumos.append(span(k, k + 1, "insumo"))
                if tokens[k].word in MEANS:
                    out.meios_execucao.append(span(k, k + 1, "meio_execucao"))
                if tokens[k].word in ACCESSORY:
                    end = k + 1
                    while end < stop and tokens[end].word not in {",", "e"}:
                        end += 1
                    out.obrigacoes_acessorias.append(span(k, end, "obrigacao_acessoria"))
            if nature == "LOCACAO" and any(t.word in {"motorista", "motoristas", "operador", "operadores"} for t in chunk):
                nature = "LOCACAO_OPERADA"

    if any(t.word in {"nao", "somente", "apenas", "exclusivamente"} for t in tokens):
        # Preserve restrictions even if the grammar cannot resolve their scope.
        out.limitacoes.append(description)
        if any(t.word == "nao" for t in tokens):
            out.motivos.append("NEGACAO_NAO_RESOLVIDA")
    out.ambiguidade = bool(out.motivos)
    out.natureza_contratual = None if out.ambiguidade else nature
    return out


def decide(obligation: Obligation, *, official_evidence=False) -> dict:
    origin = "INFERENCIA_ORIENTADA" if official_evidence else "INFERENCIA_GOVERNADA"
    if obligation.ambiguidade or not obligation.natureza_contratual:
        return {"resultado": "REVISAO", "classificacao_origem": "NAO_CLASSIFICADO",
                "regra": None, "regra_versao": RULE_VERSION, "classificador_versao": VERSION,
                "representacao": asdict(obligation), "garantia_documental": "NAO_INVESTIGADA"}
    # Only OBRA has an authorized commercial rule. Other natures remain known
    # natures with a pending commercial decision, not silently discarded.
    obra = obligation.natureza_contratual == "OBRA"
    return {"resultado": "PEDE_GARANTIA" if obra else "REGRA_GSB_PENDENTE",
            "classificacao_origem": origin, "regra": "OBRA_PEDE_GARANTIA" if obra else None,
            "regra_versao": RULE_VERSION, "classificador_versao": VERSION,
            "representacao": asdict(obligation), "garantia_documental": "NAO_INVESTIGADA"}
