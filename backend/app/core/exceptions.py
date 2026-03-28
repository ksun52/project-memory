class AppException(Exception):
    def __init__(
        self,
        status_code: int = 500,
        error_code: str = "internal_error",
        message: str = "An unexpected error occurred",
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(message)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(status_code=401, error_code="unauthorized", message=message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(status_code=404, error_code="not_found", message=message)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(status_code=403, error_code="forbidden", message=message)


class ValidationError(AppException):
    def __init__(self, message: str = "Validation error"):
        super().__init__(status_code=400, error_code="validation_error", message=message)
