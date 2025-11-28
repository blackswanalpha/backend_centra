"""
Custom middleware for security headers and other cross-cutting concerns.
"""


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to all responses.
    
    This middleware adds the following security headers:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains (HTTPS only)
    - Content-Security-Policy: default-src 'self'
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation=(), microphone=(), camera=()
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add HSTS header for HTTPS connections
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' http://localhost:* http://127.0.0.1:*; "
            "frame-ancestors 'none';"
        )
        
        # Permissions Policy (formerly Feature-Policy)
        response['Permissions-Policy'] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        return response


class RateLimitHeadersMiddleware:
    """
    Middleware to add rate limit information to responses.
    
    This middleware adds headers to inform clients about rate limiting:
    - X-RateLimit-Limit: Maximum number of requests allowed
    - X-RateLimit-Remaining: Number of requests remaining
    - X-RateLimit-Reset: Time when the rate limit resets
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add rate limit headers if available
        if hasattr(request, 'limited') and request.limited:
            response['X-RateLimit-Limit'] = getattr(request, 'limit', 'N/A')
            response['X-RateLimit-Remaining'] = getattr(request, 'remaining', 'N/A')
            response['X-RateLimit-Reset'] = getattr(request, 'reset', 'N/A')
        
        return response

