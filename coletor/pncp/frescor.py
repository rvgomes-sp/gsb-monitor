"""Frescor do EVT-007 — idade da homologação que chegou (dataResultado × dataInclusao).

Descoberta empírica (perfil temporal 17-21/08): delta grande = BACKFILL histórico
(órgão/plataforma subindo legado de 2022-2024), não atraso operacional. Mas não se
pode transformar todo delta calendário >1 em lixo: sexta→segunda é D+1 operacional
(delta_calendar=3, delta_business=1).

Estados:
  FRESH                     delta_business <= 1  (D0/D1 operacional)  -> radar comercial
  FRESH_CALENDAR_EXCEPTION  delta_calendar > 1 mas delta_business <= 1 (ex.: sex->seg) -> radar
  BACKFILL                  delta_business > 1  -> só auditoria, fora do radar
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

FRESH = "FRESH"
FRESH_CALENDAR_EXCEPTION = "FRESH_CALENDAR_EXCEPTION"
BACKFILL = "BACKFILL"


def _d(s):
    try:
        return date.fromisoformat(str(s)[:10]) if s else None
    except ValueError:
        return None


def _dt(s):
    try:
        return datetime.fromisoformat(str(s)[:19]) if s else None
    except ValueError:
        return None


def dias_uteis(inicio: date, fim: date) -> int:
    """Dias úteis (seg-sex) entre inicio (exclusivo) e fim (inclusivo). Ignora feriados."""
    if fim <= inicio:
        return 0
    dias = 0
    d = inicio
    while d < fim:
        d = date.fromordinal(d.toordinal() + 1)
        if d.weekday() < 5:  # 0-4 = seg-sex
            dias += 1
    return dias


@dataclass
class Frescor:
    data_resultado: date | None
    data_inclusao: datetime | None
    delta_calendar_days: int | None
    delta_business_days: int | None
    classe: str

    @property
    def no_radar(self) -> bool:
        return self.classe in (FRESH, FRESH_CALENDAR_EXCEPTION)


def avaliar(data_resultado, data_inclusao) -> Frescor:
    dr, di = _d(data_resultado), _dt(data_inclusao)
    if not dr or not di:
        return Frescor(dr, di, None, None, BACKFILL)
    cal = (di.date() - dr).days
    biz = dias_uteis(dr, di.date())
    if biz <= 1:
        classe = FRESH if cal <= 1 else FRESH_CALENDAR_EXCEPTION
    else:
        classe = BACKFILL
    return Frescor(dr, di, cal, biz, classe)
