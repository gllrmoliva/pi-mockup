from enum import StrEnum


class DeliverableStatus(StrEnum):
    PENDING = "pendiente"
    SUBMITTED = "entregado"
    CHANGES_REQUESTED = "cambios_solicitados"
    APPROVED = "aprobado"


class ReviewDecision(StrEnum):
    APPROVED = "aprobado"
    CHANGES_REQUESTED = "cambios_solicitados"


class ForumMessageType(StrEnum):
    USER = "usuario"
    SYSTEM = "sistema"
