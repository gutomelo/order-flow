"""Períodos do dashboard (docs/domain/dashboard.md) — regra pura, testável sem banco.

Todo período termina **agora** e começa à meia-noite (fuso do negócio) de N-1 dias atrás. O período
anterior é o mesmo intervalo deslocado N dias para trás: "hoje até as 15h" compara com "ontem até
as 15h", e não com o dia de ontem inteiro (que sempre pareceria maior).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal
from zoneinfo import ZoneInfo


class PeriodKey(StrEnum):
    TODAY = "today"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"


DAYS = {PeriodKey.TODAY: 1, PeriodKey.LAST_7_DAYS: 7, PeriodKey.LAST_30_DAYS: 30}


@dataclass(frozen=True)
class Period:
    key: PeriodKey
    start: datetime
    end: datetime
    previous_start: datetime
    previous_end: datetime
    bucket: Literal["hour", "day"]  # granularidade dos gráficos

    def slots(self) -> list[datetime]:
        """Início de cada barra do gráfico (inclusive as vazias), no fuso do negócio."""
        step = timedelta(hours=1) if self.bucket == "hour" else timedelta(days=1)
        slots, cursor = [], self.start
        while cursor < self.end:
            slots.append(cursor)
            cursor = _add(cursor, step)
        return slots


def _add(moment: datetime, step: timedelta) -> datetime:
    """Soma em "relógio de parede": meia-noite + 1 dia = meia-noite, mesmo se o fuso mudar."""
    tz = moment.tzinfo
    naive = moment.replace(tzinfo=None) + step
    return naive.replace(tzinfo=tz)


def resolve_period(key: PeriodKey, now: datetime, time_zone: str) -> Period:
    tz = ZoneInfo(time_zone)
    local_now = now.astimezone(tz)
    days = DAYS[key]
    midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = _add(midnight, timedelta(days=-(days - 1)))
    shift = timedelta(days=-days)
    return Period(
        key=key,
        start=start,
        end=local_now,
        previous_start=_add(start, shift),
        previous_end=_add(local_now, shift),
        bucket="hour" if key == PeriodKey.TODAY else "day",
    )
