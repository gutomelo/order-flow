from enum import StrEnum


class ShipmentStatus(StrEnum):
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"


class DeliverySource(StrEnum):
    """Quem confirmou a entrega: o rastreio da transportadora ou uma pessoa da logística."""

    PROVIDER = "PROVIDER"
    MANUAL = "MANUAL"
