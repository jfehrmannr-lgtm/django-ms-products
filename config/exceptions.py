from typing import Any

from django.db.models.deletion import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(
    exc: Exception,
    context: dict[str, Any],
) -> Response | None:
    if isinstance(exc, ProtectedError):
        return Response(
            {
                "error": {
                    "code": "RESOURCE_IN_USE",
                    "message": "Resource cannot be deleted because it is in use.",
                }
            },
            status=status.HTTP_409_CONFLICT,
        )
        
    return exception_handler(exc, context)
    