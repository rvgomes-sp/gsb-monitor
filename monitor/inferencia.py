#!/usr/bin/env python3
"""Redução de objeto + inferência do tipo de trabalho (para a fila do monitor).

Determinístico: NÃO inventa. Deriva do texto do objeto (limpando boilerplate de
edital) e do classificador já validado (classe_obra + itens). O objetivo é dar à
linha do monitor um rótulo claro do trabalho — "o que é a obra" — para a
prospecção, na diretriz do Rodrigo: frescor + valor + objeto claro.
"""
from __future__ import annotations

import re

# prefixos-boilerplate de edital que não informam o objeto em si
# prefixos-boilerplate removidos ITERATIVAMENTE (um por passada, até estabilizar).
# Cada item consome um pedaço da abertura administrativa até sobrar o objeto real.
_BOILERPLATE = [
    r"^\[[^\]]*\]\s*-?\s*",                       # [Portal de Compras...] -
    r"^o?\s*objeto\s+d[ao]\s+presente\s+(licita[çc][ãa]o|certame|contrata[çc][ãa]o)\s+[ée]\s+a?\s*",
    r"^constitui\s+objeto\s+d[eo].*?:\s*",
    r"^contrata[çc][ãa]o\s+integrada\s+",
    r"^contrata[çc][ãa]o\s+(tem\s+por\s+objeto\s+)?",
    r"^sele[çc][ãa]o\s+de\s+(propostas|empresas?)\s+",
    r"^presta[çc][ãa]o\s+de\s+",
    r"^de\s+empresas?\s+",
    r"^especializada\s+",
    r"^(comuns?\s+)?(no\s+ramo\s+)?d[eo]\s+engenharia\s+",
    r"^para\s+(a\s+|o\s+)?",
    r"^a?\s*execu[çc][ãa]o,?\s+(de\s+)?(obras?\s+)?(de\s+)?",
    r"^realiza[çc][ãa]o\s+(de\s+)?(servi[çc]os?\s+)?(de\s+)?",
    r"^elabora[çc][ãa]o\s+de\s+projetos?\s+(b[áa]sico\s+)?(e\s+)?(executivo\s+)?(e\s+)?",
    r"^servi[çc]os?\s+(comuns?\s+)?(cont[íi]nuos?\s+)?(de\s+engenharia\s+)?(de\s+)?",
    r"^obras?\s+(de\s+)?",
]

# fragmentos de regime de execução no início ("por empreitada por preço global, de ...")
_REGIME = re.compile(
    r"^(,?\s*)?(a\s+)?(execu[çc][ãa]o\s+)?(,?\s*)?por\s+empreitada(\s+por\s+pre[çc]o\s+"
    r"(global|unit[áa]rio|integral))?\s*[,.:]?\s*(d[aeo]s?\s+)?",
    re.IGNORECASE,
)

# corta caudas administrativas ("conforme...", "em atendimento a...", "de acordo com...")
_CAUDA = re.compile(
    r"\s*[,.;]?\s*(conforme|em\s+atendimento|de\s+acordo\s+com|observad[ao]s?|"
    r"nos\s+termos|segundo\s+as\s+especifica|com\s+a\s+finalidade|para\s+a\s+finalidade|"
    r"compreendendo|constantes?\s+n[oa]|especifica[çc][õo]es\s+constantes).*$",
    re.IGNORECASE | re.DOTALL,
)

# inferência do tipo de trabalho — ordem importa (primeiro match vence)
_TIPOS: list[tuple[str, str]] = [
    (r"recapea|pavimenta|asf[áa]lt|cbuq|terraplen|drenagem\s+vi|micro?\s*revest", "Pavimentação/vias"),
    (r"rodovi|estrada|br-?\d|acesso\s+vi[áa]rio|duplica[çc]", "Infraestrutura rodoviária"),
    (r"ponte|viaduto|passarela", "Arte especial (ponte/viaduto)"),
    (r"restaur|hist[óo]ric|patrim[ôo]ni|tombad", "Restauro/patrimônio"),
    (r"hospital|upa|unidade\s+de\s+sa[úu]de|posto\s+de\s+sa[úu]de|pronto[- ]atend", "Edificação de saúde"),
    (r"escola|creche|cei\b|educa[çc]|centro\s+de\s+forma", "Edificação educacional"),
    (r"gin[áa]sio|quadra|campo\s+(de\s+)?(futebol|esportiv)|est[áa]dio|grama\s+sint", "Equipamento esportivo"),
    (r"drenagem|esgot|saneament|adutora|esta[çc][ãa]o\s+de\s+tratam|barragem|reservat", "Saneamento/hídrica"),
    (r"ilumina|el[ée]tric|subesta[çc]|rede\s+de\s+distribui", "Infraestrutura elétrica"),
    (r"habita|unidades\s+habitac|casas\s+popular|minha\s+casa", "Habitacional"),
    (r"pra[çc]a|parque|urbaniza|paisagism|revitaliza[çc][ãa]o\s+urban", "Urbanização/espaço público"),
    (r"pr[ée]dio|edif[íi]c|constru[çc][ãa]o\s+de|sede|bloco", "Edificação"),
    (r"reforma|reparo|amplia[çc]|adequa[çc]|revitaliza|manuten[çc][ãa]o\s+predial", "Reforma/adequação predial"),
    (r"conserva[çc]|recupera[çc]|manuten[çc]", "Conservação/manutenção"),
]


def reduzir_objeto(objeto: str, limite: int = 90) -> str:
    """Objeto limpo: tira boilerplate de edital e cauda administrativa, trunca por cláusula."""
    t = re.sub(r"\s+", " ", (objeto or "")).strip()
    # remove prefixos administrativos iterativamente (até nada mais casar)
    for _ in range(12):
        antes = t
        t = _REGIME.sub("", t).lstrip(" -–—,.;")
        for pat in _BOILERPLATE:
            m = re.match(pat, t.lower())
            if m:
                t = t[m.end():].lstrip(" -–—,.;")
                break
        if t == antes:
            break
    t = _CAUDA.sub("", t).strip(" -–—.,;")
    if len(t) > limite:
        corte = t[:limite]
        # trunca na última fronteira de palavra
        sp = corte.rsplit(" ", 1)[0]
        t = (sp if len(sp) > limite * 0.6 else corte).rstrip(" -–—.,;") + "…"
    return t or (objeto or "")[:limite]


def inferir_trabalho(objeto: str, classe: str | None = None) -> str:
    """Rótulo curto do tipo de trabalho, inferido do objeto (fallback pela classe)."""
    low = re.sub(r"\s+", " ", (objeto or "")).lower()
    for pat, rotulo in _TIPOS:
        if re.search(pat, low):
            return rotulo
    if classe == "OBRA_FORTE":
        return "Obra (a detalhar)"
    if classe == "REVISAR":
        return "Obra a revisar"
    return "Serviço/indeterminado"


def rotulo_linha(objeto: str, classe: str | None = None) -> tuple[str, str]:
    """Retorna (objeto_reduzido, inferencia_trabalho) para a linha do monitor."""
    return reduzir_objeto(objeto), inferir_trabalho(objeto, classe)


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    caminho = sys.argv[1] if len(sys.argv) > 1 else "saidas/obras_20260820_final.json"
    d = json.loads(Path(caminho).read_text(encoding="utf-8"))
    for o in d.get("oportunidades", []):
        red, inf = rotulo_linha(o.get("objeto", ""), o.get("classe_obra"))
        print(f"[{inf}] {red}")
        print(f"    ← {(o.get('objeto') or '')[:100]}")
