"""Corridas de SG2 contra CU4 e AD3 (docs/domain/customers.md)."""

import threading
import time
from collections.abc import Callable
from typing import Any

import pytest
from django.db import connection

from apps.customers.exceptions import SegmentInUse
from apps.customers.models import Customer, CustomerAddress, CustomerSegment
from apps.customers.services import _roles, addresses, customers, segments
from apps.customers.tests.factories import make_customer, make_segment
from shared.testing.documents import generate_cnpj

pytestmark = [pytest.mark.concurrency, pytest.mark.django_db(transaction=True)]


def _run_concurrently(*tasks: Callable[[], str]) -> list[str]:
    barrier = threading.Barrier(len(tasks))
    outcomes: list[str] = []

    def runner(task: Callable[[], str]) -> None:
        try:
            barrier.wait()
            outcomes.append(task())
        except Exception as exc:
            outcomes.append(type(exc).__name__)
        finally:
            connection.close()

    threads = [threading.Thread(target=runner, args=(task,)) for task in tasks]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return outcomes


def test_segment_cannot_be_deactivated_while_a_customer_joins_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem o lock no segmento, a inativação contaria zero clientes ativos enquanto o cadastro,
    que já viu o segmento ativo, ainda não foi gravado."""
    segment = make_segment()
    customer_checked_segment = threading.Event()
    original = customers._lock_available_segment

    def check_then_pause(*args: Any, **kwargs: Any) -> CustomerSegment:
        result = original(*args, **kwargs)
        customer_checked_segment.set()
        time.sleep(0.5)  # cadastro em andamento, segmento já verificado
        return result

    monkeypatch.setattr(customers, "_lock_available_segment", check_then_pause)

    def create() -> str:
        customers.create_customer(
            segment.organization_id,
            customers.CustomerData(
                legal_name="Cliente Novo", tax_id=generate_cnpj(), segment_id=segment.id
            ),
        )
        return "created"

    def deactivate() -> str:
        customer_checked_segment.wait(timeout=5)
        segments.set_segment_active(CustomerSegment.objects.get(id=segment.id), is_active=False)
        return "deactivated"

    outcomes = _run_concurrently(create, deactivate)

    assert sorted(outcomes) == [SegmentInUse.__name__, "created"]
    assert CustomerSegment.objects.get(id=segment.id).is_active is True


def test_concurrent_first_addresses_leave_exactly_one_holder_per_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem o lock no cliente, as duas requisições veriam "nenhum endereço" e disputariam os papéis:
    uma delas falharia no UNIQUE parcial."""
    customer = make_customer()
    original = _roles.lock_customer

    def lock_then_pause(customer_id: Any) -> Customer:
        locked = original(customer_id)
        time.sleep(0.3)  # alarga a janela entre "verificar" e "gravar"
        return locked

    monkeypatch.setattr(addresses, "lock_customer", lock_then_pause)

    def add(label: str) -> Callable[[], str]:
        def task() -> str:
            addresses.add_address(
                customer,
                addresses.AddressData(
                    label=label,
                    postal_code="01310100",
                    street="Rua A",
                    number="1",
                    district="Centro",
                    city="São Paulo",
                    state="SP",
                ),
            )
            return "added"

        return task

    outcomes = _run_concurrently(add("A"), add("B"))

    assert outcomes == ["added", "added"]
    rows = CustomerAddress.objects.filter(customer=customer)
    assert sum(a.is_billing for a in rows) == 1
    assert sum(a.is_default_shipping for a in rows) == 1


def test_reactivation_waits_for_segment_deactivation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reativar um cliente enquanto o segmento é inativado: um dos dois precisa perder."""
    segment = make_segment()
    customer = make_customer(organization=segment.organization, segment=segment, is_active=False)
    deactivation_counted = threading.Event()
    original_save = CustomerSegment.save

    def save_after_pause(self: CustomerSegment, *args: Any, **kwargs: Any) -> None:
        deactivation_counted.set()
        time.sleep(0.5)  # inativação já contou zero clientes ativos
        original_save(self, *args, **kwargs)

    monkeypatch.setattr(CustomerSegment, "save", save_after_pause)

    def deactivate() -> str:
        segments.set_segment_active(CustomerSegment.objects.get(id=segment.id), is_active=False)
        return "deactivated"

    def reactivate() -> str:
        deactivation_counted.wait(timeout=5)
        customers.set_customer_active(Customer.objects.get(id=customer.id), is_active=True)
        return "reactivated"

    outcomes = _run_concurrently(deactivate, reactivate)

    assert sorted(outcomes) == ["SegmentNotAvailable", "deactivated"]
    assert Customer.objects.get(id=customer.id).is_active is False
