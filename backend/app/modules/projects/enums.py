from enum import StrEnum


class ProjectType(StrEnum):
    MEMOIR = "memoria"
    THESIS = "tesis"
    RESEARCH = "investigacion"


class ProjectStatus(StrEnum):
    ACTIVE = "activo"
    CLOSED = "cerrado"


class ParticipantRole(StrEnum):
    MANAGER = "gestor"
    COLLABORATOR = "colaborador"


class MilestoneStatus(StrEnum):
    PENDING = "pendiente"
    IN_PROGRESS = "en_curso"
    COMPLETED = "completado"
