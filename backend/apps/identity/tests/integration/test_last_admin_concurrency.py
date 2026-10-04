"""ID5 sob concorrência: dois ADMINs rebaixando um ao outro ao mesmo tempo.

Sem o lock da organização, as duas transações contariam "1 outro ADMIN" e ambas passariam,
deixando a organização sem administrador.

Para tornar a corrida determinística, cada thread, logo após contar os ADMINs, espera a outra
(até 1 s) antes de gravar. Com o lock, a segunda thread fica bloqueada antes de contar, a espera
da primeira expira e ela conclui; sem o lock, as duas contam ao mesmo tempo e o teste falha.
"""

import contextlib
import threading
from collections.abc import Callable
from uuid import UUID

import pytest
from django.db import connection

from apps.identity.application.commands import users as user_commands
from apps.identity.application.commands.users import ChangeUserRole, ChangeUserRoleCommand
from apps.identity.domain.exceptions import LastAdminRequired
from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import make_organization, make_user

pytestmark = [pytest.mark.concurrency, pytest.mark.django_db(transaction=True)]


def _count_then_wait_for_the_other_thread(
    original: Callable[[UUID, UUID], int], rendezvous: threading.Barrier
) -> Callable[[UUID, UUID], int]:
    def wrapper(organization_id: UUID, excluding: UUID) -> int:
        result = original(organization_id, excluding)
        # Barreira quebrada por timeout = a outra thread está bloqueada no lock (esperado).
        with contextlib.suppress(threading.BrokenBarrierError):
            rendezvous.wait(timeout=1)
        return result

    return wrapper


def test_two_admins_demoting_each_other_never_leave_the_organization_without_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organization = make_organization()
    first = make_user(organization=organization, role=Role.ADMIN)
    second = make_user(organization=organization, role=Role.ADMIN)
    start = threading.Barrier(2)
    monkeypatch.setattr(
        user_commands,
        "_other_active_admins",
        _count_then_wait_for_the_other_thread(
            user_commands._other_active_admins, threading.Barrier(2)
        ),
    )
    outcomes: list[str] = []

    def demote(actor: User, target: User) -> None:
        try:
            start.wait()
            ChangeUserRole().execute(
                ChangeUserRoleCommand(
                    organization_id=organization.id,
                    actor_id=actor.id,
                    user_id=target.id,
                    role=Role.SALES,
                )
            )
            outcomes.append("demoted")
        except LastAdminRequired:
            outcomes.append("rejected")
        finally:
            connection.close()

    threads = [
        threading.Thread(target=demote, args=(first, second)),
        threading.Thread(target=demote, args=(second, first)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["demoted", "rejected"]
    active_admins = User.objects.filter(organization=organization, role=Role.ADMIN, is_active=True)
    assert active_admins.count() == 1
