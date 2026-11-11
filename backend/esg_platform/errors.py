"""
Centralized error handling: every error leaves the API as JSON shaped
{"error": "<human message>", "code": "<machine code>", "details": {...}?}.
"""
import logging

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404, JsonResponse
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger('esg_platform.errors')


def _first_message(detail):
    """Pull one readable sentence out of DRF's nested error detail."""
    if isinstance(detail, dict):
        for key, value in detail.items():
            msg = _first_message(value)
            return msg if key in ('detail', 'non_field_errors') else f'{key}: {msg}'
    if isinstance(detail, list) and detail:
        return _first_message(detail[0])
    return str(detail)


def api_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(exc.messages)
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = exception_handler(exc, context)
    if response is None:
        logger.exception('Unhandled API error', exc_info=exc)
        return Response(
            {'error': 'Internal server error.', 'code': 'server_error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    body = {'error': _first_message(response.data), 'code': getattr(exc, 'default_code', 'error')}
    if isinstance(exc, exceptions.ValidationError):
        body['code'] = 'validation_error'
        body['details'] = response.data
    if isinstance(exc, exceptions.Throttled) and exc.wait:
        body['retry_after'] = int(exc.wait)
    response.data = body
    return response


def json_404(request, exception=None):
    return JsonResponse({'error': 'Not found.', 'code': 'not_found'}, status=404)


def json_500(request):
    return JsonResponse({'error': 'Internal server error.', 'code': 'server_error'}, status=500)
