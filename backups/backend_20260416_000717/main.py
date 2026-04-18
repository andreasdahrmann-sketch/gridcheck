from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import GridCheckInput, GridCheckOutput
from engine import run_analysis
import json, os
from datetime import datetime

app = FastAPI(title="GridCheck Pro", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])

AUDIT_DIR = "audit_log"
os.makedirs(AUDIT_DIR, exist_ok=True)

def save_audit(inp, out):
    record = {"analysis_id": out.analysis_id, "timestamp": out.timestamp.isoformat(),
              "engine_version": out.engine_version, "input": inp.dict(), "output": out.dict()}
    fn = f"{AUDIT_DIR}/{out.timestamp.strftime('%Y%m%d_%H%M%S')}_{out.analysis_id[:8]}.json"
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(record, default=str, fp=f, indent=2, ensure_ascii=False)

@app.post("/api/check", response_model=GridCheckOutput)
async def check_grid(data: GridCheckInput):
    try:
        result = run_analysis(data)
        save_audit(data, result)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Berechnungsfehler: {str(e)}")

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.1.0"}

@app.get("/api/cables")
async def get_cables():
    from constants import CABLE_DATABASE
    return CABLE_DATABASE

@app.get("/api/defaults/{voltage_level}")
async def get_defaults(voltage_level: str):
    from constants import REFERENCE_VALUES, TRAFO_DEFAULTS, DEFAULT_CABLE, VOLTAGE_LEVELS
    if voltage_level not in VOLTAGE_LEVELS:
        raise HTTPException(status_code=404, detail=f"Unbekannt: {voltage_level}")
    return {"voltage": VOLTAGE_LEVELS[voltage_level], "reference": REFERENCE_VALUES[voltage_level],
            "trafo": TRAFO_DEFAULTS[voltage_level], "default_cable": DEFAULT_CABLE[voltage_level]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
