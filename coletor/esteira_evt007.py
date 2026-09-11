#!/usr/bin/env python3
"""Entrada canônica 003-S/02-R: resultados factuais -> identidade oficial.

O fluxo histórico está preservado em esteira_evt007_legacy.py e não é importado.
"""
try:
    from .evt007_catalog_bridge import main
except ImportError:
    from evt007_catalog_bridge import main

if __name__ == "__main__":
    raise SystemExit(main())
