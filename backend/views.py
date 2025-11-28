"""
Custom views for backend-level functionality.
"""
from django.http import JsonResponse


def ratelimit_error(request, exception=None):
    """
    Custom view for rate limit exceeded errors.
    Returns a JSON response with 429 status code.
    """
    return JsonResponse({
        'success': False,
        'error': 'Rate limit exceeded. Please try again later.',
        'detail': 'Too many requests. Please slow down and try again in a few moments.'
    }, status=429)

