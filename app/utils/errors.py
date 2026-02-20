from fastapi import HTTPException, status


class NotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


def not_found_exception(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def forbidden_exception(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def bad_request_exception(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
