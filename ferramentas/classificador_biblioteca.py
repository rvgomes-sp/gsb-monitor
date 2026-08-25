#!/usr/bin/env python3
"""Classificador da BIBLIOTECA (objeto -> id_biblioteca), com as 8 regras do Rodrigo.

Saída por objeto: familia, codigo_objeto (O.01..X.00), grupo (O/S/B/C/X),
garantia_grau (CERTEZA/EXIGE/PROVAVEL/POSSIVEL/DEPENDE/IMPROVAVEL),
garantia_codigo (G0/G1/ND.A..ND.D/ND.Z), garantia_status (EXIGE/ND),
garantia_prioridade (0..9) e id_biblioteca.

As regras de garantia foram calibradas contra o golden set rotulado por Rodrigo
(21/08). Nada é descartado: incerto vira ND, mas guarda a qualificação inicial.
"""
from __future__ import annotations

import re

# ---- família (regex ampliado com as correções vistas em produção) ----
REGRAS_FAMILIA: list[tuple[str, str]] = [
    # serviço financeiro (folha/banco) — NÃO é garantia; sai do X
    (r"institui[çc][ãa]o\s+financeira|folha\s+de\s+pagament|servi[çc]os?\s+banc[áa]ri|cart[ãa]o.*benef[íi]ci|\bbacen\b",
     "SERVICO_FINANCEIRO"),
    (r"concess[ãa]o|\bppp\b|parceria\s+p[úu]blico", "CONCESSAO_PPP"),
    # fiscalização/supervisão/gerenciamento de obra = serviço de engenharia (EXIGE) — regra Rodrigo
    (r"fiscaliza[çc][ãa]o\s+de\s+obra|supervis[ãa]o\s+de\s+obra|gerenciamento\s+de\s+obra|supervis[ãa]o.*engenharia|apoio\s+[àa]\s+fiscaliza|gerenciamento.*engenharia",
     "SERVICO_ENGENHARIA"),
    (r"pavimenta|recapea|asf[áa]lt|cbuq|\btsd\b|terraplen|paralelep[íi]pedo|intertravad|micro\s*revest",
     "OBRA_PAVIMENTACAO"),
    (r"rodovi|\bbr-?\d|\bma-?\d|\bmt-?\d|\bms-?\d|\bgo-?\d|\bpb-?\d|estrada|duplica[çc]|restaura[çc][ãa]o\s+rodovi|malha\s+rodovi",
     "OBRA_RODOVIA"),
    (r"ponte|viaduto|passarela|\boae\b|obra\s+de\s+arte", "OBRA_ARTE_ESPECIAL"),
    (r"esgot|\bete\b|\beee\b|adutora|reservat[óo]ri|barragem|drenagem|a[çc]ude|abastecimento\s+de\s+[áa]gua|saneament|\bsaa\b|\bses\b|esta[çc][ãa]o\s+de\s+tratam",
     "OBRA_SANEAMENTO"),
    (r"linha\s+de\s+transmiss|subesta[çc]|rede\s+de\s+distribui|fotovoltaic|il?umina[çc][ãa]o\s+p[úu]blica",
     "OBRA_ELETRICA"),
    # material laboratorial ANTES de edificação (evita 'laborat' cair em obra)
    (r"material\s+laborator|insumos?\s+de\s+laborat|reagente|material\s+m[ée]dic|material\s+hospitalar",
     "MEDICAMENTO_SAUDE"),
    (r"constru[çc][ãa]o|edifica[çc]|\bupa\b|hospital|escola|creche|\bcei\b|gin[áa]sio|quadra|pr[ée]dio|sede|penitenci|reforma|revitaliza|requalifica|amplia[çc]|infraestrutura\s+urban|parque|urbaniza|obras?\s+comuns?|implanta[çc][ãa]o\s+de\s+usina|usina\s+de\s+triagem|engenharia.*execu[çc]|execu[çc][ãa]o\s+d[aeo]s?\s+obra|projetos?\s+b[áa]sic|projetos?\s+executiv",
     "OBRA_EDIFICACAO"),
    (r"servi[çc]os?\s+(comuns?\s+)?de\s+engenharia|engenharia\s+.*manuten[çc]|manuten[çc][ãa]o\s+predial|manuten[çc][ãa]o\s+rodovi|conserva[çc][ãa]o.*(via|logradouro|rodovi)",
     "SERVICO_ENGENHARIA"),
    (r"limpeza|vigil[âa]ncia|seguran[çc]a|portaria|serventia|conserva[çc][ãa]o\s+e\s+limp|terceiriza|m[ãa]o\s+de\s+obra|brigad|recep[çc]|dedica[çc][ãa]o\s+exclusiv|serventes?",
     "SERVICO_CONTINUO_MAO_OBRA"),
    (r"medicament|f[áa]rmac|\bopme\b|[óo]rtese|pr[óo]tese|dieta|seringa|odontol[óo]gic|enfermagem|hospitalar|vacina|imuniza|kit\s+para\s+ajuda|curativ",
     "MEDICAMENTO_SAUDE"),
    (r"alimenta[çc]|g[êe]nero|merenda|nutri[çc]|carne|latic[íi]nio|frango|refei[çc]|marmitex",
     "ALIMENTACAO"),
    (r"combust[íi]ve|[óo]leo\s+diesel|arla|gasolina|etanol", "COMBUSTIVEL"),
    (r"ve[íi]cul|caminh[ãa]o|caminhonete|motociclet|\bm[áa]quina|trator|[ôo]nibus|pneu|c[âa]mara\s+de\s+ar",
     "VEICULO_MAQUINA"),
    (r"tom[óo]graf|mobili[áa]ri|ar\s+condicionad|equipament|aparelho|notebook|microcomputad|computador|servidor|inform[áa]tica|telecom",
     "EQUIPAMENTO_MOBILIARIO"),
    (r"software|licenciament|solu[çc][ãa]o\s+integrad|tecnologia\s+da\s+informa|seguran[çc]a\s+da\s+informa|conectividade|sistema\b",
     "TI_SOFTWARE"),
    (r"hortifruti|hortigranjeiro|subsist[êe]ncia", "ALIMENTACAO"),
    (r"tubo|conex[ãa]o|\bpvc\b|\bpead\b|a[çc]os?\s+e\s+ferros?|vergalh[ãa]o|cimento|material.*constru[çc][ãa]o|uniforme|vestu[áa]rio|\bepis?\b|descart[áa]vel|papelaria|expediente|utens[íi]lio|playground|material\s+escolar|bens\s+comuns|material\s+de\s+consumo",
     "MATERIAL_INSUMO"),
    (r"loca[çc][ãa]o", "LOCACAO"),
    (r"publicidade|propaganda|marketing|consultoria|regulariza[çc][ãa]o\s+fundi|ensino\s+superior|\bies\b|transporte|gr[áa]fic|abastec|gerenciament|res[íi]duos?\s+s[óo]lid|destina[çc][ãa]o",
     "SERVICO_DIVERSO"),
]

FAMILIA_CODIGO = {
    "OBRA_EDIFICACAO": ("O.01", "O"), "OBRA_PAVIMENTACAO": ("O.02", "O"),
    "OBRA_SANEAMENTO": ("O.03", "O"), "OBRA_RODOVIA": ("O.04", "O"),
    "OBRA_ELETRICA": ("O.05", "O"), "OBRA_ARTE_ESPECIAL": ("O.06", "O"),
    "SERVICO_ENGENHARIA": ("O.07", "O"),
    "SERVICO_CONTINUO_MAO_OBRA": ("S.01", "S"), "TI_SOFTWARE": ("S.02", "S"),
    "SERVICO_DIVERSO": ("S.03", "S"), "LOCACAO": ("S.04", "S"),
    "SERVICO_FINANCEIRO": ("S.05", "S"),
    "MEDICAMENTO_SAUDE": ("B.01", "B"), "ALIMENTACAO": ("B.02", "B"),
    "COMBUSTIVEL": ("B.03", "B"), "VEICULO_MAQUINA": ("B.04", "B"),
    "EQUIPAMENTO_MOBILIARIO": ("B.05", "B"), "MATERIAL_INSUMO": ("B.06", "B"),
    "CONCESSAO_PPP": ("C.01", "C"), "OUTRO": ("X.00", "X"),
}

GAR_COD = {"CERTEZA": ("G0", "EXIGE", 0), "EXIGE": ("G1", "EXIGE", 0),
           "PROVAVEL": ("ND.A", "ND", 1), "POSSIVEL": ("ND.B", "ND", 2),
           "DEPENDE": ("ND.C", "ND", 3), "IMPROVAVEL": ("ND.D", "ND", 4),
           "ND_VAZIO": ("ND.Z", "ND", 9)}

# base de garantia por família (grau inicial)
GAR_BASE = {
    "OBRA_EDIFICACAO": "EXIGE", "OBRA_PAVIMENTACAO": "EXIGE", "OBRA_SANEAMENTO": "EXIGE",
    "OBRA_RODOVIA": "EXIGE", "OBRA_ELETRICA": "EXIGE", "OBRA_ARTE_ESPECIAL": "EXIGE",
    "SERVICO_ENGENHARIA": "EXIGE", "SERVICO_CONTINUO_MAO_OBRA": "EXIGE",
    "CONCESSAO_PPP": "CERTEZA",
    "MEDICAMENTO_SAUDE": "PROVAVEL",   # regra 1: valor+tipo
    "COMBUSTIVEL": "PROVAVEL",         # regra 5
    "TI_SOFTWARE": "PROVAVEL",         # provável
    "ALIMENTACAO": "IMPROVAVEL", "MATERIAL_INSUMO": "IMPROVAVEL",
    "EQUIPAMENTO_MOBILIARIO": "IMPROVAVEL", "VEICULO_MAQUINA": "IMPROVAVEL",
    "LOCACAO": "IMPROVAVEL", "SERVICO_DIVERSO": "DEPENDE",
    "SERVICO_FINANCEIRO": "IMPROVAVEL", "OUTRO": "ND_VAZIO",
}


def _familia(low: str) -> str:
    for pat, fam in REGRAS_FAMILIA:
        if re.search(pat, low):
            return fam
    return "OUTRO"


def _refina_garantia(fam: str, low: str, base: str) -> str:
    # regra 3: alimentação PREPARADA no local = serviço -> provável
    if fam == "ALIMENTACAO" and re.search(r"prepar|nas\s+depend[êe]nci|cozinha|coletiva", low):
        return "PROVAVEL"
    # regra 4: uniforme/material escolar -> provável
    if fam == "MATERIAL_INSUMO" and re.search(r"uniforme|material\s+escolar", low):
        return "PROVAVEL"
    # regra 2: fornecimento + instalação/montagem/mão de obra -> possível
    if fam in ("EQUIPAMENTO_MOBILIARIO", "MATERIAL_INSUMO") and re.search(
            r"instala[çc][ãa]o|montagem|m[ãa]o\s+de\s+obra", low):
        return "POSSIVEL"
    return base


def classificar(objeto: str) -> dict:
    low = re.sub(r"\s+", " ", (objeto or "")).lower()
    fam = _familia(low)
    cod_obj, grupo = FAMILIA_CODIGO[fam]
    grau = _refina_garantia(fam, low, GAR_BASE[fam])
    gc, status, prio = GAR_COD[grau]
    return {"familia": fam, "codigo_objeto": cod_obj, "grupo": grupo,
            "garantia_grau": grau, "garantia_codigo": gc,
            "garantia_status": status, "garantia_prioridade": prio,
            "id_biblioteca": f"{cod_obj}-{gc}"}


# ---- validação contra o golden set (21/08) ----
if __name__ == "__main__":
    import json
    import sys
    from collections import Counter
    arq = sys.argv[1] if len(sys.argv) > 1 else "saidas/biblioteca_rotulada_20260821.json"
    rows = json.load(open(arq, encoding="utf-8"))
    ok_status = ok_grupo = 0
    conf = Counter()
    erros_status = []
    for r in rows:
        m = classificar(r["objeto"])
        humano_grau = r["garantia_grau"]  # já normalizado (EXIGE/PROVAVEL/IMPROVAVEL/CERTEZA/DEPENDE/VAZIO)
        humano_status = "EXIGE" if humano_grau in ("EXIGE", "CERTEZA") else ("ND" if humano_grau != "VAZIO" else "ND")
        if m["garantia_status"] == humano_status:
            ok_status += 1
        else:
            erros_status.append((m["codigo_objeto"], m["garantia_status"], humano_status, r["objeto"][:70]))
        conf[(m["garantia_status"], humano_status)] += 1
    n = len(rows)
    print(f"golden set: {n} objetos")
    print(f"acerto de STATUS (EXIGE vs ND): {ok_status}/{n} = {ok_status/n:.0%}")
    print("matriz (maq_status, humano_status): ", dict(conf))
    print(f"\ndivergências de status ({len(erros_status)}):")
    for c, mq, hu, obj in erros_status[:40]:
        print(f"  [{c}] maq={mq} humano={hu} | {obj}")
