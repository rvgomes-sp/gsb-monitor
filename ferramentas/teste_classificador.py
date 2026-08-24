#!/usr/bin/env python3
"""Teste de regressão do classificador de obra contra o golden set.

Roda classificador.classificar_objeto() em cada caso de config/corpus_regressao_obra.json
e compara com classe_esperada. LIMITROFE é aceito se cair em LIMITROFE (ou REVISAR na
projeção de produção). Falha = patch rejeitado.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "coletor"))
from pncp import classificador as clf  # noqa: E402

CORPUS = Path(__file__).resolve().parents[1] / "config" / "corpus_regressao_obra.json"


def main() -> int:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    ok = falhas = 0
    print(f"{'id':32} {'esperado':32} {'obtido':32} status")
    print("-" * 108)
    for c in corpus["casos"]:
        esp = c["classe_esperada"]
        obt, motivo = clf.classificar_objeto(c["objeto"])
        acerto = (obt == esp)
        # aceite: negativos e positivos têm de bater exato; LIMITROFE aceita LIMITROFE
        status = "OK" if acerto else "FALHA"
        if acerto:
            ok += 1
        else:
            falhas += 1
        print(f"{c['id'][:32]:32} {esp:32} {obt:32} {status}")
        if not acerto:
            print(f"    motivo obtido: {motivo}")
            print(f"    objeto: {c['objeto'][:110]}")
    print("-" * 108)
    print(f"RESULTADO: {ok}/{ok+falhas} OK | {falhas} falha(s)")
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
