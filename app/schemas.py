from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ---- Action items ----
class ActionItemBase(BaseModel):
    description: str
    owner: Optional[str] = "client"
    done: Optional[bool] = False


class ActionItemCreate(ActionItemBase):
    pass


class ActionItemUpdate(BaseModel):
    description: Optional[str] = None
    owner: Optional[str] = None
    done: Optional[bool] = None


class ActionItemOut(ActionItemBase):
    id: int
    session_id: int

    class Config:
        from_attributes = True


# ---- Sessions ----
class SessionBase(BaseModel):
    session_type: Optional[str] = "discovery"
    session_date: Optional[str] = None
    next_session_date: Optional[str] = None
    pain: Optional[str] = None
    duration: Optional[str] = None
    why_now: Optional[str] = None
    tried: Optional[str] = None
    cost_scale: Optional[int] = None
    outcome: Optional[str] = None
    technique: Optional[str] = None
    goal_1: Optional[str] = None
    goal_2: Optional[str] = None
    goal_detail: Optional[str] = None
    goal_why: Optional[str] = None
    work_what: Optional[str] = None
    work_stop: Optional[str] = None
    progress_review: Optional[str] = None
    win: Optional[str] = None
    obstacles: Optional[str] = None
    goal_shift: Optional[str] = None
    session_focus: Optional[str] = None
    cadence: Optional[str] = None
    excited: Optional[str] = None
    notes: Optional[str] = None


class SessionCreate(SessionBase):
    pass


class SessionOut(SessionBase):
    id: int
    client_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    action_items: List[ActionItemOut] = []

    class Config:
        from_attributes = True


class SessionSummary(BaseModel):
    """Lightweight version for sidebar/session-list rendering."""
    id: int
    session_type: Optional[str] = "discovery"
    session_date: Optional[str] = None
    next_session_date: Optional[str] = None

    class Config:
        from_attributes = True


# ---- Clients ----
class ClientBase(BaseModel):
    name: str = ""
    source: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientOut(ClientBase):
    id: int
    created_at: Optional[datetime] = None
    sessions: List[SessionSummary] = []

    class Config:
        from_attributes = True
