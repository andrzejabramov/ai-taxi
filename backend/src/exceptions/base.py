"""
Базовые исключения приложения
"""


class BaseAppException(Exception):
    """Базовый класс для всех исключений приложения"""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ValidationError(BaseAppException):
    """Ошибка валидации данных"""

    pass


class DatabaseError(BaseAppException):
    """Ошибка при работе с БД"""

    pass


class ExternalServiceError(BaseAppException):
    """Ошибка внешнего сервиса (2GIS, OpenRouter и т.д.)"""

    pass
