from django_filters import rest_framework as filters
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.audit.api.serializers import AuditLogSerializer
from apps.audit.domain.entries import AuditAction, EntityType
from apps.audit.models import AuditLog
from apps.identity.domain.permissions import Permission
from shared.permissions import HasPermission
from shared.tenancy.api import TenantScopedQuerysetMixin


class AuditLogFilter(filters.FilterSet):  # type: ignore[misc]  # django-filter não tem tipos
    action = filters.MultipleChoiceFilter(choices=[(a.value, a.value) for a in AuditAction])
    entity_type = filters.ChoiceFilter(choices=[(e.value, e.value) for e in EntityType])
    occurred_after = filters.IsoDateTimeFilter(field_name="occurred_at", lookup_expr="gte")
    occurred_before = filters.IsoDateTimeFilter(field_name="occurred_at", lookup_expr="lt")

    class Meta:
        model = AuditLog
        fields = ("action", "entity_type", "entity_id", "order_id", "actor")


class AuditLogViewSet(
    TenantScopedQuerysetMixin, mixins.ListModelMixin, viewsets.GenericViewSet[AuditLog]
):
    """Trilha de auditoria da organização: só leitura (não há criar, editar nem apagar)."""

    queryset = AuditLog.objects.select_related("actor")
    serializer_class = AuditLogSerializer
    permission_classes = (IsAuthenticated, HasPermission(Permission.AUDIT_READ))
    filterset_class = AuditLogFilter
    search_fields = ("entity_label", "reason")
    ordering = ("-occurred_at",)
