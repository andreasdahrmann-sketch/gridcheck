# Hilfsskript: Erstellt main.py
import os

code = r"""from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
import os as _os

from engine.berechnung import berechnung, LEITUNGSTYPEN, TRAFOTYPPEN
from engine.ki_modul import ki_bewertung
from engine.revision import speichere_revision, pruefe_integritaet
from app.db.database import get_db, engine as db_engine, Base
from app.models.project import Project, AnalysisResult, KITrainingData

Base.metadata.create_all(bind=db_engine)

app = FastAPI(title="GridCheck Pro", version="2.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

frontend_path = _os.path.join(_os.path.dirname(__file__), "..", "frontend")
if _os.path.exists(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")


class AnalyseRequest(BaseModel):
    projekt_name: Optional[str] = "Unbenannt"
    plz: Optional[str] = ""
    nennspannung: float = Field(..., description="kV")
    leistung_mw: float = Field(..., gt=0)
    cos_phi: float = Field(0.95, ge=0.8, le=1.0)
    kurzschlussleistung_mva: Optional[float] = None
    entfernung_km: float = Field(0.5, gt=0)
    leitungstyp: str = Field("NAYY 4x150")
    anzahl_parallele_systeme: int = Field(1, ge=1, le=6)
    trafo_typ: Optional[str] = None
    anschlussart: str = Field("einspeisung")
    erzeugungstyp: Optional[str] = Field("pv")


class FeedbackRequest(BaseModel):
    revision_id: str
    nb_decision: str
    corrections: Optional[dict] = None


def _extract_ampel(ergebnis: dict) -> str:
    fazit = ergebnis.get("fazit", "").upper()
    if "MACHBAR" in fazit:
        return "gruen"
    if "KRITISCH" in fazit or "NICHT" in fazit:
        return "rot"
    return "gelb"


@app.get("/")
async def root():
    return FileResponse(_os.path.join(frontend_path, "index.html"))


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/api/referenz")
async def referenzdaten():
    return {
        "leitungstypen": list(LEITUNGSTYPEN.keys()),
        "trafotypen": list(TRAFOTYPPEN.keys()),
        "spannungsebenen": [0.4, 10, 20, 110],
        "erzeugungstypen": ["pv", "wind", "batterie", "bhkw"]
    }


@app.post("/api/check")
async def netzcheck(req: AnalyseRequest, db: Session = Depends(get_db)):
    eingabe = {
        "nennspannung": req.nennspannung,
        "leistung_mw": req.leistung_mw,
        "cos_phi": req.cos_phi,
        "entfernung_km": req.entfernung_km,
        "leitungstyp": req.leitungstyp,
        "anzahl_parallele_systeme": req.anzahl_parallele_systeme,
        "anschlussart": req.anschlussart,
        "erzeugungstyp": req.erzeugungstyp,
    }
    if req.kurzschlussleistung_mva:
        eingabe["kurzschlussleistung_mva"] = req.kurzschlussleistung_mva
    if req.trafo_typ:
        eingabe["trafo_typ"] = req.trafo_typ

    try:
        ergebnis = berechnung(eingabe)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    ergebnis = ki_bewertung(ergebnis)
    ergebnis = speichere_revision(ergebnis)

    try:
        project = Project(name=req.projekt_name, plz=req.plz, status="analysiert", eingabe_json=eingabe)
        db.add(project)
        db.flush()
        analysis = AnalysisResult(
            project_id=project.id, version=1,
            eingabe_parameter=eingabe, ergebnis_json=ergebnis,
            ampel_status=_extract_ampel(ergebnis),
            revision_hash=ergebnis.get("revision", {}).get("hash", "")
        )
        db.add(analysis)
        ki_data = KITrainingData(
            input_features=eingabe,
            result_ampel=_extract_ampel(ergebnis),
            region_plz=req.plz
        )
        db.add(ki_data)
        db.commit()
        db.refresh(project)
        ergebnis["project_id"] = project.id
    except Exception as e:
        db.rollback()
        ergebnis["db_fehler"] = str(e)

    return ergebnis


@app.post("/api/feedback")
async def feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    ki_entry = db.query(KITrainingData).order_by(KITrainingData.id.desc()).first()
    if ki_entry:
        ki_entry.nb_decision = req.nb_decision
        ki_entry.corrections = req.corrections
        db.commit()
    return {"status": "ok"}


@app.get("/api/revision/check")
async def revision_check():
    return pruefe_integritaet()


@app.get("/api/projekte")
async def projekte_liste(db: Session = Depends(get_db)):
    projekte = db.query(Project).order_by(Project.created_at.desc()).limit(50).all()
    return [{"id": p.id, "name": p.name, "plz": p.plz, "status": p.status, "created_at": str(p.created_at)} for p in projekte]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

with open("main.py", "w", encoding="utf-8") as f:
    f.write(code)
print(f"main.py erstellt: {len(code)} Zeichen")
