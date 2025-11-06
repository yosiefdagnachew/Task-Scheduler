"""Database models and configuration."""

from datetime import date, datetime
from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.types import TypeDecorator, VARCHAR
import json
from typing import List, Set
import os
from .models import TaskType

Base = declarative_base()


class JSONEncodedSet(TypeDecorator):
    """Store Python sets as JSON strings."""
    impl = VARCHAR
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(list(value))
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return set(json.loads(value))
        return set()


class JSONEncodedList(TypeDecorator):
    """Store Python lists as JSON strings."""
    impl = VARCHAR
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return []


class TeamMemberDB(Base):
    """Database model for team members."""
    __tablename__ = "team_members"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    office_days = Column(JSONEncodedSet, default=set)
    created_at = Column(Date, default=date.today)
    updated_at = Column(Date, default=date.today, onupdate=date.today)
    
    # Relationships
    unavailable_periods = relationship("UnavailablePeriod", back_populates="member", cascade="all, delete-orphan")
    assignments = relationship("AssignmentDB", back_populates="assignee")
    fairness_counts = relationship("FairnessCount", back_populates="member", cascade="all, delete-orphan")


class UnavailablePeriod(Base):
    """Database model for unavailable periods."""
    __tablename__ = "unavailable_periods"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(String, ForeignKey("team_members.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(Date, default=date.today)
    
    # Relationships
    member = relationship("TeamMemberDB", back_populates="unavailable_periods")


class AssignmentDB(Base):
    """Database model for task assignments."""
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    member_id = Column(String, ForeignKey("team_members.id"), nullable=False)
    assignment_date = Column(Date, nullable=False)
    week_start = Column(Date, nullable=True)  # For SysAid weekly assignments
    created_at = Column(Date, default=date.today)
    
    # Relationships
    assignee = relationship("TeamMemberDB", back_populates="assignments")


class FairnessCount(Base):
    """Database model for tracking assignment counts."""
    __tablename__ = "fairness_counts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(String, ForeignKey("team_members.id"), nullable=False)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    count = Column(Integer, default=0)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    updated_at = Column(Date, default=date.today, onupdate=date.today)
    
    # Relationships
    member = relationship("TeamMemberDB", back_populates="fairness_counts")


class ScheduleDB(Base):
    """Database model for schedules."""
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(String, nullable=True)
    status = Column(String, default="draft")  # draft, published, archived


class TaskTypeDef(Base):
    """Configurable task type definition (e.g., ATM, SysAid)."""
    __tablename__ = "task_type_defs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    recurrence = Column(String, nullable=False)  # daily, weekly, monthly
    required_count = Column(Integer, default=1)
    role_labels = Column(JSONEncodedList, default=list)  # ["A", "B"] etc.
    rules_json = Column(Text, nullable=True)  # advanced rules JSON


class ShiftDef(Base):
    """Shift definition for a task type."""
    __tablename__ = "shift_defs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type_id = Column(Integer, ForeignKey("task_type_defs.id"), nullable=False)
    label = Column(String, nullable=False)
    start_time = Column(String, nullable=False)  # HH:MM
    end_time = Column(String, nullable=False)    # HH:MM
    required_count = Column(Integer, default=1)
    
    task_type = relationship("TaskTypeDef")


class SwapRequest(Base):
    """Represents a swap or replacement request for an assignment."""
    __tablename__ = "swap_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    requested_by = Column(String, ForeignKey("team_members.id"), nullable=False)
    proposed_member_id = Column(String, ForeignKey("team_members.id"), nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.now)
    decided_at = Column(DateTime, nullable=True)
    
    assignment = relationship("AssignmentDB")
    requested_by_member = relationship("TeamMemberDB", foreign_keys=[requested_by])
    proposed_member = relationship("TeamMemberDB", foreign_keys=[proposed_member_id])


class User(Base):
    """Application user for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="member")  # member, admin (extensible)
    created_at = Column(DateTime, default=datetime.now)
    member_id = Column(String, ForeignKey("team_members.id"), nullable=True)
    must_change_password = Column(Boolean, default=False)

class Database:
    """Database connection and session management."""
    
    def __init__(self, database_url: str | None = None):
        url = database_url or os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "DATABASE_URL is not set. Please create a .env with your Postgres URL, e.g. "
                "DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/iss_task_schedule"
            )
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, connect_args=connect_args)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
        # Best-effort ensure new columns exist (esp. for existing DBs without alembic)
        with self.engine.connect() as conn:
            try:
                conn.execute("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0")
            except Exception:
                pass
    
    def get_session(self):
        """Get a database session."""
        return self.SessionLocal()
    
    def close(self):
        """Close database connection."""
        self.engine.dispose()


# Global database instance
db = Database()

