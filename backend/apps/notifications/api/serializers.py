from typing import Any

from rest_framework import serializers


class NotificationSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    status = serializers.CharField()
    recipient = serializers.CharField(help_text="E-mail mascarado (ma***@empresa.com).")
    subject = serializers.CharField()
    attempts = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    sent_at = serializers.DateTimeField(allow_null=True)
