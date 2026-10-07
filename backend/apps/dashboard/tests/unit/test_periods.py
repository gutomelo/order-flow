from datetime import UTC, datetime, timedelta

import pytest

from apps.dashboard.domain.periods import PeriodKey, resolve_period

SP = "America/Sao_Paulo"
# 7/10/2026 15:30 em São Paulo (UTC-3)
NOW = datetime(2026, 10, 7, 18, 30, tzinfo=UTC)


def _local(period_value: datetime) -> str:
    return period_value.strftime("%d/%m %H:%M")


def test_today_starts_at_local_midnight_and_compares_with_yesterday_until_the_same_time() -> None:
    period = resolve_period(PeriodKey.TODAY, NOW, SP)

    assert (_local(period.start), _local(period.end)) == ("07/10 00:00", "07/10 15:30")
    assert (_local(period.previous_start), _local(period.previous_end)) == (
        "06/10 00:00",
        "06/10 15:30",
    )
    assert period.bucket == "hour"
    assert len(period.slots()) == 16  # 00h…15h


@pytest.mark.parametrize(("key", "days", "first_day"), [("7d", 7, "01/10"), ("30d", 30, "08/09")])
def test_last_n_days_include_today_and_compare_with_the_n_days_before(
    key: str, days: int, first_day: str
) -> None:
    period = resolve_period(PeriodKey(key), NOW, SP)

    assert _local(period.start) == f"{first_day} 00:00"
    assert period.bucket == "day"
    assert len(period.slots()) == days
    assert period.previous_start == period.start - timedelta(days=days)
    assert period.previous_end == period.end - timedelta(days=days)


def test_the_business_day_is_not_the_utc_day() -> None:
    # 02:00 UTC do dia 8 ainda é dia 7 (23:00) em São Paulo.
    period = resolve_period(PeriodKey.TODAY, datetime(2026, 10, 8, 2, 0, tzinfo=UTC), SP)

    assert _local(period.start) == "07/10 00:00"
