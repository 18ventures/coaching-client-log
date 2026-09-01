from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    source = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sessions = relationship("Session", back_populates="client", cascade="all, delete-orphan", order_by="Session.session_date.desc()")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    session_type = Column(String, default="discovery")  # "discovery" (session 1) or "followup" (session 2+)

    session_date = Column(String)       # ISO date string
    next_session_date = Column(String)  # ISO date string

    # The pain point (discovery)
    pain = Column(Text)
    duration = Column(String)
    why_now = Column(Text)
    tried = Column(Text)
    cost_scale = Column(Integer)  # 1-10

    # What we could achieve together (discovery)
    outcome = Column(Text)
    technique = Column(Text)
    goal_1 = Column(String)
    goal_2 = Column(String)
    goal_detail = Column(Text)
    goal_why = Column(Text)

    # Their work (discovery)
    work_what = Column(Text)
    work_stop = Column(Text)

    # Reviewing last session (followup)
    progress_review = Column(Text)   # what they actually did since last time
    win = Column(Text)               # biggest win since last session
    obstacles = Column(Text)         # what got in the way / didn't happen

    # Goals check-in (followup)
    goal_shift = Column(Text)        # any change in goals, or new goals surfacing

    # This session (followup)
    session_focus = Column(Text)     # what we're focusing on today and why

    # Logistics / notes (both)
    cadence = Column(String)
    excited = Column(Text)
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="sessions")
    action_items = relationship("ActionItem", back_populates="session", cascade="all, delete-orphan")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    description = Column(String, nullable=False)
    owner = Column(String, default="client")  # "client" or "coach"
    done = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="action_items")
