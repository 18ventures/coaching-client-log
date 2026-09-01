from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session as DBSession, joinedload
from sqlalchemy import desc
import os
import csv
import io

from . import models, schemas
from .database import get_db
from .notes_parser import parse_notes_image

# Schema is now owned by Alembic migrations (see /migrations), not created here.
# Run `alembic upgrade head` before starting the app — see Procfile / railway.json.

app = FastAPI(title="Coaching Client Log")

# Serves manifest.json + icons for "Add to Home Screen" support. This folder
# must contain at least one file for git/GitHub to track it — an empty
# directory won't survive a push, which will crash this mount on deploy.
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    index_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(index_path, "r") as f:
        return f.read()


# ---------------- Clients ----------------

@app.get("/api/clients", response_model=list[schemas.ClientOut])
def list_clients(db: DBSession = Depends(get_db)):
    clients = db.query(models.Client).options(joinedload(models.Client.sessions)).order_by(desc(models.Client.created_at)).all()
    return clients


@app.get("/api/clients/{client_id}", response_model=schemas.ClientOut)
def get_client(client_id: int, db: DBSession = Depends(get_db)):
    client = db.query(models.Client).options(joinedload(models.Client.sessions)).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@app.post("/api/clients", response_model=schemas.ClientOut)
def create_client(client: schemas.ClientCreate, db: DBSession = Depends(get_db)):
    db_client = models.Client(**client.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client


@app.put("/api/clients/{client_id}", response_model=schemas.ClientOut)
def update_client(client_id: int, client: schemas.ClientCreate, db: DBSession = Depends(get_db)):
    db_client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    for key, value in client.model_dump().items():
        setattr(db_client, key, value)
    db.commit()
    db.refresh(db_client)
    return db_client


@app.delete("/api/clients/{client_id}")
def delete_client(client_id: int, db: DBSession = Depends(get_db)):
    db_client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(db_client)
    db.commit()
    return {"ok": True}


# ---------------- Sessions ----------------

@app.post("/api/clients/{client_id}/sessions", response_model=schemas.SessionOut)
def create_session(client_id: int, session: schemas.SessionCreate, db: DBSession = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db_session = models.Session(client_id=client_id, **session.model_dump())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


@app.get("/api/sessions/{session_id}", response_model=schemas.SessionOut)
def get_session(session_id: int, db: DBSession = Depends(get_db)):
    db_session = db.query(models.Session).options(joinedload(models.Session.action_items)).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return db_session


@app.put("/api/sessions/{session_id}", response_model=schemas.SessionOut)
def update_session(session_id: int, session: schemas.SessionCreate, db: DBSession = Depends(get_db)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    for key, value in session.model_dump().items():
        setattr(db_session, key, value)
    db.commit()
    db.refresh(db_session)
    return db_session


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: int, db: DBSession = Depends(get_db)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(db_session)
    db.commit()
    return {"ok": True}


# ---------------- Action items ----------------

@app.post("/api/sessions/{session_id}/actions", response_model=schemas.ActionItemOut)
def create_action(session_id: int, action: schemas.ActionItemCreate, db: DBSession = Depends(get_db)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    db_action = models.ActionItem(session_id=session_id, **action.model_dump())
    db.add(db_action)
    db.commit()
    db.refresh(db_action)
    return db_action


@app.put("/api/actions/{action_id}", response_model=schemas.ActionItemOut)
def update_action(action_id: int, action: schemas.ActionItemUpdate, db: DBSession = Depends(get_db)):
    db_action = db.query(models.ActionItem).filter(models.ActionItem.id == action_id).first()
    if not db_action:
        raise HTTPException(status_code=404, detail="Action item not found")
    for key, value in action.model_dump(exclude_unset=True).items():
        setattr(db_action, key, value)
    db.commit()
    db.refresh(db_action)
    return db_action


@app.delete("/api/actions/{action_id}")
def delete_action(action_id: int, db: DBSession = Depends(get_db)):
    db_action = db.query(models.ActionItem).filter(models.ActionItem.id == action_id).first()
    if not db_action:
        raise HTTPException(status_code=404, detail="Action item not found")
    db.delete(db_action)
    db.commit()
    return {"ok": True}


# ---------------- Notes photo parsing ----------------

@app.post("/api/parse-notes")
async def parse_notes(
    file: UploadFile = File(...),
    session_type: str = Form("discovery"),
):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"):
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}")

    image_bytes = await file.read()
    if len(image_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 15MB)")

    # Claude's vision API expects jpeg/png/webp/gif — convert heic if needed is out of
    # scope here, so we pass content_type through as-is and let the API validate it.
    media_type = file.content_type

    try:
        parsed = parse_notes_image(image_bytes, media_type, session_type)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error parsing notes: {e}")

    return parsed


# ---------------- Export ----------------

@app.get("/api/export")
def export_csv(db: DBSession = Depends(get_db)):
    sessions = db.query(models.Session).options(
        joinedload(models.Session.client),
        joinedload(models.Session.action_items),
    ).all()

    output = io.StringIO()
    fieldnames = [
        "client_name", "session_type", "session_date", "next_session_date", "pain", "duration",
        "why_now", "tried", "cost_scale", "outcome", "technique", "goal_1", "goal_2",
        "goal_detail", "goal_why", "work_what", "work_stop",
        "progress_review", "win", "obstacles", "goal_shift", "session_focus",
        "cadence", "excited", "notes", "action_items",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for s in sessions:
        actions_str = "; ".join(
            f"[{'x' if a.done else ' '}] {a.description}" for a in s.action_items
        )
        writer.writerow({
            "client_name": s.client.name if s.client else "",
            "session_type": s.session_type,
            "session_date": s.session_date,
            "next_session_date": s.next_session_date,
            "pain": s.pain, "duration": s.duration, "why_now": s.why_now, "tried": s.tried,
            "cost_scale": s.cost_scale, "outcome": s.outcome, "technique": s.technique,
            "goal_1": s.goal_1, "goal_2": s.goal_2, "goal_detail": s.goal_detail,
            "goal_why": s.goal_why, "work_what": s.work_what, "work_stop": s.work_stop,
            "progress_review": s.progress_review, "win": s.win, "obstacles": s.obstacles,
            "goal_shift": s.goal_shift, "session_focus": s.session_focus,
            "cadence": s.cadence, "excited": s.excited, "notes": s.notes,
            "action_items": actions_str,
        })
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=client_log_export.csv"},
    )
