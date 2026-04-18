from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import engine, Base
from api.routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GridCheck Pro API",
    version="1.0.0",
    description="Pre-Netzanschluss-Check mit N-1 Analyse, Diagnose und KI-Lernmodul",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {"status": "GridCheck API running", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}
