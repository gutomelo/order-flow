import uuid

import pytest

from apps.identity.domain.exceptions import LastAdminRequired, SelfManagementNotAllowed
from apps.identity.domain.policies import (
    ensure_admin_remains,
    ensure_not_managing_self,
    is_active_admin,
)

pytestmark = pytest.mark.unit


def test_user_cannot_manage_themselves() -> None:
    same = uuid.uuid4()

    with pytest.raises(SelfManagementNotAllowed):
        ensure_not_managing_self(same, same)


def test_managing_another_user_is_allowed() -> None:
    ensure_not_managing_self(uuid.uuid4(), uuid.uuid4())


def test_removing_the_last_active_admin_is_rejected() -> None:
    with pytest.raises(LastAdminRequired):
        ensure_admin_remains(
            target_is_active_admin=True, target_will_be_active_admin=False, other_active_admins=0
        )


def test_removing_an_admin_when_others_remain_is_allowed() -> None:
    ensure_admin_remains(
        target_is_active_admin=True, target_will_be_active_admin=False, other_active_admins=1
    )


@pytest.mark.parametrize(
    ("is_admin_before", "is_admin_after"), [(False, False), (False, True), (True, True)]
)
def test_changes_that_do_not_remove_an_admin_are_allowed(
    is_admin_before: bool, is_admin_after: bool
) -> None:
    ensure_admin_remains(
        target_is_active_admin=is_admin_before,
        target_will_be_active_admin=is_admin_after,
        other_active_admins=0,
    )


def test_inactive_admin_is_not_an_active_admin() -> None:
    assert is_active_admin(role="ADMIN", is_active=False) is False
    assert is_active_admin(role="ADMIN", is_active=True) is True
    assert is_active_admin(role="SALES", is_active=True) is False
