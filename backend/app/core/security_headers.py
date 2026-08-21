"""
Baseline security headers on every response. This is a JSON API (plus
one WebSocket endpoint), not a page-rendering server, so the CSP here
is deliberately minimal and defensive rather than tuned for restricting
inline scripts/styles the way a page-serving app's would be — there's
no HTML being served by this backend to protect. HSTS is the header
that matters most here.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Only meaningful once actually served over HTTPS (Railway
        # terminates TLS in front of the app) — harmless over local HTTP.
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        # Minimal CSP appropriate for a JSON API: no content is rendered
        # here, so this mainly guards the rare case of someone loading
        # an API response directly in a browser tab.
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response
