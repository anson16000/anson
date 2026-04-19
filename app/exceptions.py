from __future__ import annotations


class AppException(Exception):
    def __init__(self, message: str, code: int = 500, details: dict | None = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class ValidationException(AppException):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code=400, details=details)


class NotFoundException(AppException):
    def __init__(self, resource: str, identifier):
        super().__init__(f"{resource} not found: {identifier}", code=404)
