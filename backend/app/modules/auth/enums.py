from enum import StrEnum


class UserType(StrEnum):
    PROFESSOR = "profesor"
    STUDENT = "estudiante"


class UserStatus(StrEnum):
    INVITED = "invitada"
    ACTIVE = "activa"
