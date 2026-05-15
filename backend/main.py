from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response
from core.config import settings
from api.routes import router
from api.stakeholders import router as stakeholder_router
from api.analyze_v2 import router_v2
from api.v1_projektierer import router as v1_projektierer_router
from api.v1_geo import router as v1_geo_router
from api.v1_ki_feedback import router as v1_ki_router
from api.revisions import router as revisions_router
from api.auth import router as auth_router
from api.billing import router as billing_router
from api.ops_followups import router as ops_followups_router
from api.projects import router as projects_router
from api.site_markers import router as site_markers_router
from api.users import router as users_router
from api.contact import router as contact_router
from api.analytics import router as analytics_router
from api.v2_reports import router_reports

app = FastAPI(
    title="GridCheck Pro API",
    version=settings.app_version,
    description="Pre-Netzanschluss-Check mit N-1 Analyse, Diagnose und KI-Lernmodul",
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next) -> Response:
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(self), microphone=(), camera=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
        )
        return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID", "X-CSRF-Token"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

# v2 zuerst: dieselbe Pfadfamilie (/api/v1/analyze...) darf nie vom Legacy-/Persist-Router ueberschrieben werden.
app.include_router(router_v2, prefix="/api/v1")
app.include_router(router)
app.include_router(stakeholder_router, prefix="/api/v1")
app.include_router(v1_projektierer_router)
app.include_router(v1_geo_router)
app.include_router(v1_ki_router)
app.include_router(revisions_router, prefix="/api/v1")
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(ops_followups_router)
app.include_router(projects_router)
app.include_router(site_markers_router)
app.include_router(users_router)
app.include_router(contact_router)
app.include_router(analytics_router)
app.include_router(router_reports, prefix="/api")

# Legacy-Compatibility (existing clients), gated via feature flag.
if settings.enable_legacy_routes:
    app.include_router(stakeholder_router, prefix="/api")
    app.include_router(router_v2, prefix="/api/v2")
    app.include_router(revisions_router, prefix="/api/v2")

@app.get("/")
def root():
    return {"status": "GridCheck API running", "version": app.version, "env": settings.app_env}

@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}


