from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
import os
from pathlib import Path
from app.etl.sisab import ingest_sisab_file
from app.db.models import init_db
from app.etl.reconcile import reconcile_period

app = FastAPI(title="Sisab Ingest API")

INCOMING_DIR = os.getenv("INCOMING_DIR", "./data/incoming")
Path(INCOMING_DIR).mkdir(parents=True, exist_ok=True)

@app.on_event("startup")
def startup():
    init_db()

@app.post("/upload/")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), path: str = Form(...)):
    dest_dir = Path(INCOMING_DIR) / Path(path)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file.filename
    with dest_path.open("wb") as f:
        f.write(await file.read())
    if path.startswith("sisab"):
        background_tasks.add_task(ingest_sisab_file, str(dest_path))
        return {"status": "saved", "path": str(dest_path)}
    else:
        # placeholder: fast ingestion will be implemented; save file
        return {"status": "saved", "path": str(dest_path), "note": "Aguardando ingestao FAST"}

@app.get("/reconcile/")
def reconcile(period: str):
    """Retorna discrepâncias entre FAST (agregado) e SISAB para um período (YYYY-MM)."""
    diffs = reconcile_period(period)
    return {"period": period, "diffs": diffs}
