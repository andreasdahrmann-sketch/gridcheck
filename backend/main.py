from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import engine, Base
from core.config import settings
from api.routes import router
from api.stakeholders import router as stakeholder_router
from api.analyze_v2 import router_v2
from api.v1_projektierer import router as v1_projektierer_router
from api.v1_geo import router as v1_geo_router
from api.v1_ki_feedback import router as v1_ki_router
from api.revisions import router as revisions_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GridCheck Pro API",
    version=settings.app_version,
    description="Pre-Netzanschluss-Check mit N-1 Analyse, Diagnose und KI-Lernmodul",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
)

app.include_router(router)
app.include_router(stakeholder_router, prefix="/api/v1")
app.include_router(router_v2, prefix="/api/v1")
app.include_router(v1_projektierer_router)
app.include_router(v1_geo_router)
app.include_router(v1_ki_router)
app.include_router(revisions_router, prefix="/api/v1")

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


