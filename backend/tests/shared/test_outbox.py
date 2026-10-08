"""Transactional Outbox (ADR-011): atomicidade com o negócio e entrega idempotente."""

import pytest
from django.db import transaction

from shared.events.base import DomainEvent, EventEnvelope
from shared.events.bus import deliver, publish, relay_pending, subscribe
from shared.events.models import OutboxEvent, ProcessedEvent

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

received: list[EventEnvelope] = []
failures = {"remaining": 0}


class SomethingHappened(DomainEvent):
    event_name = "tests.something.happened"


class NobodyListens(DomainEvent):
    event_name = "tests.nobody.listens"


@subscribe("tests.something.happened")
def record(event: EventEnvelope) -> None:
    if failures["remaining"]:
        failures["remaining"] -= 1
        raise RuntimeError("handler falhou")
    received.append(event)


@pytest.fixture(autouse=True)
def _reset() -> None:
    received.clear()
    failures["remaining"] = 0


def _dispatched() -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []
    relay_pending(lambda event_id, handler: calls.append((event_id, handler)))
    return calls


@pytest.mark.django_db(transaction=True)  # sem a transação que envolve cada teste
def test_publish_requires_a_transaction() -> None:
    with pytest.raises(RuntimeError, match="transação"):
        publish(SomethingHappened())


def test_a_rolled_back_change_never_emits_its_event() -> None:
    with pytest.raises(ValueError), transaction.atomic():
        publish(SomethingHappened())
        raise ValueError("regra de negócio falhou depois")

    assert not OutboxEvent.objects.exists()


def test_relay_dispatches_once_per_handler_and_marks_published() -> None:
    with transaction.atomic():
        publish(SomethingHappened())
        publish(NobodyListens())

    first = _dispatched()
    second = _dispatched()

    assert [handler for _, handler in first] == [f"{__name__}.record"]
    assert second == []
    assert OutboxEvent.objects.filter(published_at__isnull=True).count() == 0


def test_delivery_is_applied_once_even_if_repeated() -> None:
    with transaction.atomic():
        publish(SomethingHappened())
    [(event_id, handler)] = _dispatched()

    assert deliver(event_id, handler) is True
    assert deliver(event_id, handler) is False  # reentrega (at-least-once) não repete o efeito
    assert len(received) == 1
    assert received[0].event_name == "tests.something.happened"


def test_a_failed_handler_can_be_retried() -> None:
    failures["remaining"] = 1
    with transaction.atomic():
        publish(SomethingHappened())
    [(event_id, handler)] = _dispatched()

    with pytest.raises(RuntimeError):
        deliver(event_id, handler)
    assert not ProcessedEvent.objects.exists()  # falha desfaz o registro de entrega
    assert deliver(event_id, handler) is True
    assert len(received) == 1
