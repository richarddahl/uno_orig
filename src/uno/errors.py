from fastapi import HTTPException, status


class UnoError(Exception):
    message: str
    error_code: str

    def __init__(self, message, error_code):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class UnoModelConfigError(UnoError):
    pass


class UnoModelRegistryError(UnoError):
    pass


class UnoModelFieldListError(UnoError):
    pass


class UnoModelRelationConfigError(UnoError):
    pass


class UnoModelTableError(UnoError):
    pass


class UnoHTTPError(HTTPException):
    status_code = 400
    detail = "Record matching data already exists in database."


class DataExistsError(HTTPException):
    status_code = 400
    detail = "Record matching data already exists in database."


class UnauthorizedError(HTTPException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Invalid user credentials"
    headers = {"WWW-enticate": "Bearer"}


class ForbiddenError(HTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You do not have permission to access this resource."
