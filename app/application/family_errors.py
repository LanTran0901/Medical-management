"""Domain/application errors mapped to HTTP in routers."""


class FamilyAppError(Exception):
    """Base for families feature errors."""

    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(FamilyAppError):
    """404 — resource missing or out of scope."""


class ForbiddenError(FamilyAppError):
    """403 — in scope but insufficient role."""


class ConflictError(FamilyAppError):
    """409 — unique / business conflict."""


class GoneError(FamilyAppError):
    """410 — resource existed but is no longer usable (expired/revoked/consumed)."""
