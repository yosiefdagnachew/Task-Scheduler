"""FastAPI backend for task scheduler."""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
from pydantic import BaseModel, Field
import json

from .database import (
    db,
    TeamMemberDB,
    UnavailablePeriod,
    AssignmentDB,
    FairnessCount,
    DynamicFairnessCount,
    ScheduleDB,
    TaskTypeDef,
    ShiftDef,
    SwapRequest,
    User,
)
from .task_type_model import DynamicTaskType, TaskTypeShift
from .models import TaskType, TeamMember, Assignment, Schedule, FairnessLedger
from .config import SchedulingConfig
from .scheduler import Scheduler
from .export import export_to_csv, export_to_ics, export_audit_log, export_to_xlsx, export_to_excel, export_to_pdf, export_fairness_to_pdf
from .loader import load_team
from jose import jwt, JWTError
import os
from passlib.context import CryptContext
import smtplib
from email.message import EmailMessage
import secrets

app = FastAPI(title="Task Scheduler API", version="1.0.0")
# Auth helpers
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a password against a hash, with proper error handling."""
    if not plain_password or not password_hash:
        return False
    
    # Bcrypt has a 72-byte limit, ensure password is within limit
    if isinstance(plain_password, str):
        # Encode to bytes to check length
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            # Truncate to 72 bytes (not characters!)
            plain_password = password_bytes[:72].decode('utf-8', errors='ignore')
    
    try:
        return pwd_context.verify(plain_password, password_hash)
    except (ValueError, TypeError) as e:
        # Log the error but don't expose details
        print(f"Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Hash a password, ensuring it's within bcrypt's 72-byte limit."""
    if not password:
        raise ValueError("Password cannot be empty")
    
    # Bcrypt has a 72-byte limit, ensure password is within limit
    if isinstance(password, str):
        # Encode to bytes to check length
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            # Truncate to 72 bytes (not characters!)
            password = password_bytes[:72].decode('utf-8', errors='ignore')
            print(f"Warning: Password truncated to 72 bytes for bcrypt compatibility")
    
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RegisterPayload(BaseModel):
    username: str
    password: str
    role: Optional[str] = "member"
    member_id: Optional[str] = None
    must_change_password: Optional[bool] = False


# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class TeamMemberCreate(BaseModel):
    name: str
    id: str
    office_days: List[int] = Field(default=[0, 1, 2, 3, 4])
    email: Optional[str] = None
    
class TeamMemberResponse(BaseModel):
    id: str
    name: str
    office_days: List[int]
    email: Optional[str] = None
    unavailable_periods: List[dict] = []
    
    class Config:
        from_attributes = True

class UnavailablePeriodCreate(BaseModel):
    member_id: str
    start_date: date
    end_date: date
    reason: Optional[str] = None

class MemberIdUpdate(BaseModel):
    new_id: str

class ScheduleGenerateRequest(BaseModel):
    start_date: date
    end_date: date
    config_override: Optional[dict] = None
    tasks: Optional[List[str]] = None  # e.g., ["ATM", "SysAid"]
    task_members: Optional[Dict[str, List[str]]] = None  # Mapping of task type name to list of member IDs
    seed: Optional[int] = None
    fairness_aggressiveness: Optional[int] = Field(default=1, ge=1, le=5)

class AssignmentResponse(BaseModel):
    id: int
    task_type: str
    member_id: str
    member_name: str
    assignment_date: date
    week_start: Optional[date] = None
    shift_label: Optional[str] = None
    custom_task_name: Optional[str] = None
    custom_task_shift: Optional[str] = None
    recurrence: Optional[str] = None
    
    class Config:
        from_attributes = True

class ScheduleResponse(BaseModel):
    id: int
    start_date: date
    end_date: date
    status: str
    assignments: List[AssignmentResponse]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Dependency to get database session
def get_db():
    try:
        session = db.get_session()
        try:
            yield session
        finally:
            session.close()
    except Exception as e:
        # Log database connection errors
        import traceback
        print(f"Database connection error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_db)) -> User:
    cred_exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise cred_exc
    except JWTError:
        raise cred_exc
    user = session.query(User).filter(User.username == username).first()
    if not user:
        raise cred_exc
    return user

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user

def _generate_password(length: int = 10) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def _send_email(to_email: str, subject: str, body: str):
    # Primary SMTP_* envs; fallbacks support common naming like EMAIL_USERNAME
    user = os.getenv("SMTP_USER") or os.getenv("EMAIL_USERNAME")
    password = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_PASSWORD") or os.getenv("EMAIL_APP_PASSWORD")
    host = os.getenv("SMTP_HOST") or ("smtp.gmail.com" if user and user.endswith("@gmail.com") else None)
    port = int(os.getenv("SMTP_PORT", "0") or (587 if host == "smtp.gmail.com" else 0))
    from_email = os.getenv("FROM_EMAIL") or os.getenv("EMAIL_FROM") or user or "noreply@example.com"
    use_tls = (os.getenv("USE_TLS", "true").lower() == "true")
    if not host or not port or not user or not password:
        return  # SMTP not configured; skip
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(host, port, timeout=10) as server:
        if use_tls:
            server.starttls()
        server.login(user, password)
        server.send_message(msg)

# Helper functions
def db_member_to_model(db_member: TeamMemberDB, session: Session) -> TeamMember:
    """Convert database member to model."""
    unavailable_dates = set()
    unavailable_ranges = []
    
    for period in db_member.unavailable_periods:
        if period.start_date == period.end_date:
            unavailable_dates.add(period.start_date)
        else:
            unavailable_ranges.append((period.start_date, period.end_date))
    
    return TeamMember(
        name=db_member.name,
        id=db_member.id,
        office_days=db_member.office_days or {0, 1, 2, 3, 4},
        unavailable_dates=unavailable_dates,
        unavailable_ranges=unavailable_ranges,
        email=db_member.email
    )


def _task_identifier(task_type_val) -> str:
    """Normalize a task_type value to a string identifier for DB storage/queries.

    Accepts either a TaskType enum or a plain string (for dynamic tasks).
    """
    from .models import TaskType as _TaskType
    if isinstance(task_type_val, _TaskType):
        return task_type_val.value
    return str(task_type_val)


def _is_enum_task_identifier(task_identifier: str) -> bool:
    from .models import TaskType as _TaskType
    return task_identifier in {t.value for t in _TaskType}

# API Endpoints

@app.get("/")
async def root():
    return {"message": "Task Scheduler API", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

# Auth endpoints
@app.post("/api/auth/register")
async def register(payload: RegisterPayload, session: Session = Depends(get_db)):
    try:
        existing = session.query(User).filter(User.username == payload.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Validate password length
        if not payload.password:
            raise HTTPException(status_code=400, detail="Password cannot be empty")
        
        password_hash = get_password_hash(payload.password)
        user = User(
            username=payload.username, 
            password_hash=password_hash, 
            role=payload.role or "member", 
            member_id=payload.member_id, 
            must_change_password=bool(payload.must_change_password)
        )
        session.add(user)
        session.commit()
        return {"message": "Registered"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Registration error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_db)):
    try:
        user = session.query(User).filter(User.username == form_data.username).first()
        if not user:
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        
        # Validate password_hash exists and is reasonable
        if not user.password_hash:
            raise HTTPException(status_code=400, detail="User account has no password set")
        
        # Check if password_hash looks like a bcrypt hash (starts with $2a$, $2b$, or $2y$)
        if not user.password_hash.startswith(('$2a$', '$2b$', '$2y$', '$2x$')):
            raise HTTPException(
                status_code=500, 
                detail="Invalid password hash format. Please contact administrator to reset password."
            )
        
        if not verify_password(form_data.password, user.password_hash):
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        
        token = create_access_token({"sub": user.username, "role": user.role, "member_id": user.member_id})
        return TokenResponse(access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Login error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.get("/api/me")
async def me(current: User = Depends(get_current_user)):
    return {"username": current.username, "role": current.role, "member_id": current.member_id, "must_change_password": current.must_change_password}

class ChangePasswordPayload(BaseModel):
    current_password: Optional[str] = None
    new_password: str

@app.post("/api/auth/change-password")
async def change_password(payload: ChangePasswordPayload, current: User = Depends(get_current_user), session: Session = Depends(get_db)):
    # If current.must_change_password, allow without current_password; otherwise require it
    if not current.must_change_password:
        if not payload.current_password or not verify_password(payload.current_password, current.password_hash):
            raise HTTPException(status_code=400, detail="Current password incorrect")
    current.password_hash = get_password_hash(payload.new_password)
    current.must_change_password = False
    session.commit()
    return {"message": "Password changed"}

# Team Members
@app.get("/api/team-members", response_model=List[TeamMemberResponse])
async def get_team_members(session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Get all team members."""
    members = session.query(TeamMemberDB).all()
    result = []
    for member in members:
        periods = [
            {
                "id": p.id,
                "start_date": p.start_date.isoformat(),
                "end_date": p.end_date.isoformat(),
                "reason": p.reason
            }
            for p in member.unavailable_periods
        ]
        result.append({
            "id": member.id,
            "name": member.name,
            "email": member.email,
            "office_days": list(member.office_days or []),
            "unavailable_periods": periods
        })
    return result

@app.post("/api/team-members", response_model=TeamMemberResponse)
async def create_team_member(member: TeamMemberCreate, session: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Create a new team member."""
    existing = session.query(TeamMemberDB).filter(TeamMemberDB.id == member.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Member with this ID already exists")
    
    db_member = TeamMemberDB(
        id=member.id,
        name=member.name,
        office_days=set(member.office_days),
        email=member.email
    )
    session.add(db_member)
    session.commit()
    session.refresh(db_member)

    # Auto-create user account for this member with random password
    gen_password = _generate_password()
    password_hash = get_password_hash(gen_password)
    if not session.query(User).filter(User.username == member.id).first():
        user_row = User(username=member.id, password_hash=password_hash, role="member", member_id=member.id, must_change_password=True)
        session.add(user_row)
        session.commit()
        # Send welcome email if possible
        if member.email:
            try:
                _send_email(
                    to_email=member.email,
                    subject="Your Task Scheduler account",
                    body=(
                        f"Hello {member.name},\n\n"
                        f"An account has been created for you.\n"
                        f"Username: {member.id}\nPassword: {gen_password}\n\n"
                        f"Login at {os.getenv('FRONTEND_URL', 'http://localhost:3000')}/login and change your password afterwards.\n"
                    ),
                )
            except Exception:
                # ignore email failures
                pass

    return {
        "id": db_member.id,
        "name": db_member.name,
        "email": db_member.email,
        "office_days": list(db_member.office_days),
        "unavailable_periods": []
    }


def _serialize_swap(swap: SwapRequest) -> dict:
    assignment = swap.assignment
    requested_member = swap.requested_by_member
    proposed_member = swap.proposed_member
    return {
        "id": swap.id,
        "assignment_id": swap.assignment_id,
        "assignment_date": assignment.assignment_date.isoformat() if assignment else None,
        "task_type": assignment.task_type.value if assignment else None,
        "requested_by": swap.requested_by,
        "requested_by_name": requested_member.name if requested_member else None,
        "proposed_member_id": swap.proposed_member_id,
        "proposed_member_name": proposed_member.name if proposed_member else None,
        "status": swap.status,
        "reason": swap.reason,
        "created_at": swap.created_at.isoformat() if swap.created_at else None,
        "decided_at": swap.decided_at.isoformat() if swap.decided_at else None,
        "peer_decision": swap.peer_decision,
        "peer_decided_at": swap.peer_decided_at.isoformat() if swap.peer_decided_at else None,
    }

@app.post("/api/team-members/{member_id:path}/resend-credentials")
async def resend_credentials(member_id: str, session: Session = Depends(get_db), admin: User = Depends(require_admin)):
    member = session.query(TeamMemberDB).filter(TeamMemberDB.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    user_row = session.query(User).filter(User.username == member_id).first()
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")
    new_pass = _generate_password()
    user_row.password_hash = get_password_hash(new_pass)
    user_row.must_change_password = True
    session.commit()
    email_sent = False
    if member.email:
        try:
            _send_email(
                to_email=member.email,
                subject="Task Scheduler credentials reset",
                body=(
                    f"Hello {member.name},\n\n"
                    f"Your credentials have been reset.\n"
                    f"Username: {member.id}\nTemporary password: {new_pass}\n\n"
                    f"Login at {os.getenv('FRONTEND_URL', 'http://localhost:3000')}/login and change your password afterwards.\n"
                ),
            )
            email_sent = True
        except Exception:
            email_sent = False
    return {"message": "Credentials reset", "temp_password": new_pass, "email_sent": email_sent}

@app.put("/api/team-members/{member_id:path}", response_model=TeamMemberResponse)
async def update_team_member(member_id: str, member: TeamMemberCreate, session: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Update a team member."""
    db_member = session.query(TeamMemberDB).filter(TeamMemberDB.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Update fields - handle email explicitly (can be None/empty string)
    db_member.name = member.name
    db_member.office_days = set(member.office_days)
    db_member.email = member.email if member.email else None
    db_member.updated_at = date.today()
    session.commit()
    session.refresh(db_member)
    
    periods = [
        {
            "id": p.id,
            "start_date": p.start_date.isoformat(),
            "end_date": p.end_date.isoformat(),
            "reason": p.reason
        }
        for p in db_member.unavailable_periods
    ]
    
    return {
        "id": db_member.id,
        "name": db_member.name,
        "email": db_member.email,
        "office_days": list(db_member.office_days),
        "unavailable_periods": periods
    }

@app.patch("/api/team-members/{member_id:path}/id")
async def change_member_id(member_id: str, payload: MemberIdUpdate, session: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Change a member's ID and cascade to related tables."""
    if not payload.new_id:
        raise HTTPException(status_code=400, detail="new_id is required")
    existing = session.query(TeamMemberDB).filter(TeamMemberDB.id == member_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Member not found")
    if payload.new_id == member_id:
        return {"message": "No change"}
    # Ensure target ID not taken
    conflict = session.query(TeamMemberDB).filter(TeamMemberDB.id == payload.new_id).first()
    if conflict:
        raise HTTPException(status_code=400, detail="Target ID already exists")

    # Since id is a primary key, we need to create a new row and delete the old one
    # First, create new team member with new ID (copying all data)
    new_member = TeamMemberDB(
        id=payload.new_id,
        name=existing.name,
        office_days=existing.office_days.copy() if existing.office_days else set(),
        email=existing.email,
        created_at=existing.created_at,
        updated_at=date.today()
    )
    session.add(new_member)
    session.flush()  # Flush to get the new row in the database without committing

    # Now update foreign key references (new ID exists in team_members now)
    session.query(UnavailablePeriod).filter(UnavailablePeriod.member_id == member_id).update({UnavailablePeriod.member_id: payload.new_id}, synchronize_session=False)
    session.query(AssignmentDB).filter(AssignmentDB.member_id == member_id).update({AssignmentDB.member_id: payload.new_id}, synchronize_session=False)
    session.query(FairnessCount).filter(FairnessCount.member_id == member_id).update({FairnessCount.member_id: payload.new_id}, synchronize_session=False)
    session.query(SwapRequest).filter(SwapRequest.requested_by == member_id).update({SwapRequest.requested_by: payload.new_id}, synchronize_session=False)
    session.query(SwapRequest).filter(SwapRequest.proposed_member_id == member_id).update({SwapRequest.proposed_member_id: payload.new_id}, synchronize_session=False)
    
    # Update User table if username matches the old member_id
    user_row = session.query(User).filter(User.username == member_id).first()
    if user_row:
        user_row.username = payload.new_id
        user_row.member_id = payload.new_id

    # Delete old member row
    session.delete(existing)
    session.commit()
    return {"message": "Member ID updated", "id": payload.new_id}

@app.delete("/api/team-members/{member_id:path}")
async def delete_team_member(member_id: str, session: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Delete a team member and all related records."""
    db_member = session.query(TeamMemberDB).filter(TeamMemberDB.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Delete related records first to avoid foreign key violations
    # Delete swap requests where this member is involved
    session.query(SwapRequest).filter(
        (SwapRequest.requested_by == member_id) | (SwapRequest.proposed_member_id == member_id)
    ).delete(synchronize_session=False)
    
    # Delete assignments for this member
    session.query(AssignmentDB).filter(AssignmentDB.member_id == member_id).delete(synchronize_session=False)
    
    # Delete unavailable periods
    session.query(UnavailablePeriod).filter(UnavailablePeriod.member_id == member_id).delete(synchronize_session=False)
    
    # Delete fairness counts
    session.query(FairnessCount).filter(FairnessCount.member_id == member_id).delete(synchronize_session=False)
    
    # Delete user account if exists (by member_id OR username, since username is often the same as member_id)
    session.query(User).filter(
        (User.member_id == member_id) | (User.username == member_id)
    ).delete(synchronize_session=False)
    
    # Finally delete the team member
    session.delete(db_member)
    session.commit()
    return {"message": "Member deleted successfully"}

# Unavailable Periods
@app.post("/api/unavailable-periods")
async def create_unavailable_period(period: UnavailablePeriodCreate, session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Create an unavailable period for a team member."""
    member = session.query(TeamMemberDB).filter(TeamMemberDB.id == period.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Only allow members to modify their own unavailable periods unless admin
    if user.role != "admin" and user.member_id != period.member_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    db_period = UnavailablePeriod(
        member_id=period.member_id,
        start_date=period.start_date,
        end_date=period.end_date,
        reason=period.reason
    )
    session.add(db_period)
    session.commit()
    session.refresh(db_period)
    
    return {
        "id": db_period.id,
        "member_id": db_period.member_id,
        "start_date": db_period.start_date.isoformat(),
        "end_date": db_period.end_date.isoformat(),
        "reason": db_period.reason
    }

@app.delete("/api/unavailable-periods/{period_id}")
async def delete_unavailable_period(period_id: int, session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Delete an unavailable period."""
    period = session.query(UnavailablePeriod).filter(UnavailablePeriod.id == period_id).first()
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    # Only owner or admin can delete
    if user.role != "admin" and user.member_id != period.member_id:
        raise HTTPException(status_code=403, detail="Not allowed")
    session.delete(period)
    session.commit()
    return {"message": "Period deleted successfully"}

# Scheduling
@app.post("/api/schedules/generate")
async def generate_schedule(request: ScheduleGenerateRequest, session: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Generate a new schedule."""
    # Load team members from database
    db_members = session.query(TeamMemberDB).all()
    members = [db_member_to_model(m, session) for m in db_members]
    
    if not members:
        raise HTTPException(status_code=400, detail="No team members available")
    
    # Load or create config
    try:
        config = SchedulingConfig.from_yaml("data/config.yaml")
    except:
        config = SchedulingConfig()
    
    # Override config if provided
    if request.config_override:
        for key, value in request.config_override.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    # Load task types from database ONLY if specific tasks are requested
    task_types = None
    if request.tasks and len(request.tasks) > 0:
        # Load ONLY the specific task types requested (not all)
        db_task_types = session.query(TaskTypeDef).filter(TaskTypeDef.name.in_(request.tasks)).all()
        
        if db_task_types:
            # Convert database TaskTypeDef to DynamicTaskType
            task_types = []
            for db_tt in db_task_types:
                shifts = session.query(ShiftDef).filter(ShiftDef.task_type_id == db_tt.id).all()
                # Get rules for this task type
                rules = json.loads(db_tt.rules_json) if db_tt.rules_json else {}
                
                task_type_shifts = []
                for s in shifts:
                    # Check if this specific shift requires rest (can be in shift-specific rules or task-level rules)
                    shift_requires_rest = False
                    if rules.get("shifts"):
                        # Check if this shift has specific rest rule
                        shift_rule = next((sr for sr in rules.get("shifts", []) if sr.get("label") == s.label), None)
                        if shift_rule:
                            shift_requires_rest = shift_rule.get("requires_rest", False)
                        else:
                            shift_requires_rest = rules.get("requires_rest", False)
                    else:
                        shift_requires_rest = rules.get("requires_rest", False)
                    
                    task_type_shifts.append(TaskTypeShift(
                        label=s.label,
                        start_time=s.start_time,
                        end_time=s.end_time,
                        required_count=s.required_count,
                        requires_rest=shift_requires_rest
                    ))
                task_types.append(DynamicTaskType(
                    id=db_tt.id,
                    name=db_tt.name,
                    recurrence=db_tt.recurrence,
                    required_count=db_tt.required_count,
                    role_labels=db_tt.role_labels or [],
                    rules_json=json.loads(db_tt.rules_json) if db_tt.rules_json else None,
                    shifts=task_type_shifts
                ))
    
    # Load dynamic fairness counts for configurable task types
    dynamic_fairness_counts = {}
    dynamic_rows = session.query(DynamicFairnessCount).all()
    for row in dynamic_rows:
        task_counts = dynamic_fairness_counts.setdefault(row.task_name, {})
        task_counts[row.member_id] = row.count
    
    # Generate schedule
    # If task_types is provided, schedule only those tasks
    # If task_types is None, use default ATM/SysAid logic
    scheduler = Scheduler(config, dynamic_counts=dynamic_fairness_counts)
    schedule = scheduler.generate_schedule(
        members, 
        request.start_date, 
        request.end_date, 
        task_types=task_types,
        task_members=request.task_members
    )
    
    # Save to database
    db_schedule = ScheduleDB(
        start_date=request.start_date,
        end_date=request.end_date,
        status="draft",
        created_at=datetime.now()
    )
    session.add(db_schedule)
    session.flush()
    
    # Save assignments
    for assignment in schedule.assignments:
        task_id = _task_identifier(assignment.task_type)
        db_assignment = AssignmentDB(
            task_type=task_id,
            schedule_id=db_schedule.id,
            member_id=assignment.assignee.id,
            assignment_date=assignment.date,
            week_start=assignment.week_start,
            shift_label=assignment.shift_label,
            custom_task_name=assignment.custom_task_name,
            custom_task_shift=assignment.custom_task_shift,
            recurrence=assignment.recurrence
        )
        session.add(db_assignment)
        # Update fairness ledger
        # Distinguish dynamic/custom tasks vs built-in enum tasks
        if assignment.custom_task_name or (isinstance(assignment.task_type, str) and not _is_enum_task_identifier(assignment.task_type)):
            tname = assignment.custom_task_name or task_id or "CUSTOM"
            fairness_count = session.query(DynamicFairnessCount).filter(
                DynamicFairnessCount.member_id == assignment.assignee.id,
                DynamicFairnessCount.task_name == tname
            ).first()
            if not fairness_count:
                fairness_count = DynamicFairnessCount(
                    member_id=assignment.assignee.id,
                    task_name=tname,
                    count=0,
                )
                session.add(fairness_count)
            fairness_count.count += 1
            fairness_count.updated_at = date.today()
        else:
            # Enum task stored by its identifier string
            task_str = task_id
            fairness_count = session.query(FairnessCount).filter(
                FairnessCount.member_id == assignment.assignee.id,
                FairnessCount.task_type == task_str
            ).first()
            if not fairness_count:
                from datetime import timedelta
                fairness_count = FairnessCount(
                    member_id=assignment.assignee.id,
                    task_type=task_str,
                    count=0,
                    period_start=date.today() - timedelta(days=90),
                    period_end=date.today()
                )
                session.add(fairness_count)
            fairness_count.count += 1
            fairness_count.updated_at = date.today()
    
    session.commit()
    session.refresh(db_schedule)
    
    # Build response - return only assignments created for this schedule
    assignments = session.query(AssignmentDB).filter(
        AssignmentDB.schedule_id == db_schedule.id
    ).all()
    
    assignment_responses = []
    for a in assignments:
        member = session.query(TeamMemberDB).filter(TeamMemberDB.id == a.member_id).first()
        assignment_responses.append({
            "id": a.id,
            "task_type": a.task_type if isinstance(a.task_type, str) else a.task_type.value,
            "member_id": a.member_id,
            "member_name": member.name if member else "Unknown",
            "assignment_date": a.assignment_date.isoformat(),
            "week_start": a.week_start.isoformat() if a.week_start else None,
            "shift_label": a.shift_label,
            "custom_task_name": a.custom_task_name,
            "custom_task_shift": a.custom_task_shift,
            "recurrence": a.recurrence
        })
    
    return {
        "schedule_id": db_schedule.id,
        "start_date": db_schedule.start_date.isoformat(),
        "end_date": db_schedule.end_date.isoformat(),
        "status": db_schedule.status,
        "assignments": assignment_responses,
        "audit_log": scheduler.audit.get_log()
    }

@app.get("/api/schedules", response_model=List[dict])
async def get_schedules(session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Get all schedules."""
    schedules = session.query(ScheduleDB).order_by(ScheduleDB.created_at.desc()).all()
    result = []
    for s in schedules:
        result.append({
            "id": s.id,
            "start_date": s.start_date.isoformat(),
            "end_date": s.end_date.isoformat(),
            "status": s.status,
            "created_at": s.created_at.isoformat()
        })
    return result

@app.delete("/api/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int, session: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Delete a schedule and its assignments; adjust fairness counters accordingly."""
    schedule = session.query(ScheduleDB).filter(ScheduleDB.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Fetch assignments that belong to this schedule
    assignments = session.query(AssignmentDB).filter(
        AssignmentDB.schedule_id == schedule_id
    ).all()
    
    assignment_ids = [a.id for a in assignments]

    # Delete swap requests that reference these assignments first (to avoid foreign key violation)
    if assignment_ids:
        session.query(SwapRequest).filter(
            SwapRequest.assignment_id.in_(assignment_ids)
        ).delete(synchronize_session=False)

    # Decrement fairness counts for these assignments if rows exist
    for a in assignments:
        fc = session.query(FairnessCount).filter(
            FairnessCount.member_id == a.member_id,
            FairnessCount.task_type == a.task_type
        ).first()
        if fc and fc.count and fc.count > 0:
            fc.count -= 1
            fc.updated_at = date.today()

    # Delete assignments
    if assignment_ids:
        session.query(AssignmentDB).filter(
            AssignmentDB.id.in_(assignment_ids)
        ).delete(synchronize_session=False)

    # Delete schedule
    session.delete(schedule)
    session.commit()
    return {"message": "Schedule deleted"}

@app.get("/api/schedules/{schedule_id}")
async def get_schedule(schedule_id: int, session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Get a specific schedule with assignments."""
    schedule = session.query(ScheduleDB).filter(ScheduleDB.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    assignments = session.query(AssignmentDB).filter(
        AssignmentDB.schedule_id == schedule_id
    ).all()
    
    assignment_responses = []
    for a in assignments:
        member = session.query(TeamMemberDB).filter(TeamMemberDB.id == a.member_id).first()
        assignment_responses.append({
            "id": a.id,
            "task_type": a.task_type if isinstance(a.task_type, str) else a.task_type.value,
            "member_id": a.member_id,
            "member_name": member.name if member else "Unknown",
            "assignment_date": a.assignment_date.isoformat(),
            "week_start": a.week_start.isoformat() if a.week_start else None,
            "shift_label": a.shift_label,
            "custom_task_name": a.custom_task_name,
            "custom_task_shift": a.custom_task_shift,
            "recurrence": a.recurrence
        })
    
    return {
        "id": schedule.id,
        "start_date": schedule.start_date.isoformat(),
        "end_date": schedule.end_date.isoformat(),
        "status": schedule.status,
        "assignments": assignment_responses,
        "created_at": schedule.created_at.isoformat()
    }

@app.get("/api/schedules/{schedule_id}/export/csv")
async def export_schedule_csv(schedule_id: int, session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Export schedule to CSV."""
    schedule = session.query(ScheduleDB).filter(ScheduleDB.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Build schedule model
    db_members = session.query(TeamMemberDB).all()
    members_dict = {m.id: db_member_to_model(m, session) for m in db_members}
    
    assignments = session.query(AssignmentDB).filter(
        AssignmentDB.schedule_id == schedule_id
    ).all()
    
    schedule_assignments = []
    for a in assignments:
        member = members_dict.get(a.member_id)
        if member:
            assignment = Assignment(
                task_type=a.task_type,
                assignee=member,
                date=a.assignment_date,
                week_start=a.week_start,
                shift_label=a.shift_label
            )
            schedule_assignments.append(assignment)
    
    schedule_obj = Schedule(
        assignments=schedule_assignments,
        start_date=schedule.start_date,
        end_date=schedule.end_date
    )
    
    # Export
    file_path = f"out/schedule_{schedule_id}.csv"
    export_to_csv(schedule_obj, file_path)
    
    return FileResponse(file_path, media_type="text/csv", filename=f"schedule_{schedule_id}.csv")

@app.get("/api/schedules/{schedule_id}/export/xlsx")
async def export_schedule_xlsx(schedule_id: int, session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Export schedule to XLSX (vertical layout)."""
    schedule = session.query(ScheduleDB).filter(ScheduleDB.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Build schedule model
    db_members = session.query(TeamMemberDB).all()
    members_dict = {m.id: db_member_to_model(m, session) for m in db_members}

    assignments = session.query(AssignmentDB).filter(
        AssignmentDB.schedule_id == schedule_id
    ).all()

    schedule_assignments = []
    for a in assignments:
        member = members_dict.get(a.member_id)
        if member:
            assignment = Assignment(
                task_type=a.task_type,
                assignee=member,
                date=a.assignment_date,
                week_start=a.week_start,
                shift_label=a.shift_label
            )
            schedule_assignments.append(assignment)

    schedule_obj = Schedule(
        assignments=schedule_assignments,
        start_date=schedule.start_date,
        end_date=schedule.end_date
    )

    file_path = f"out/schedule_{schedule_id}.xlsx"
    export_to_xlsx(schedule_obj, file_path)
    return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=f"schedule_{schedule_id}.xlsx")

# Fairness
@app.get("/api/fairness")
async def get_fairness_counts(session: Session = Depends(get_db)):
    """Get fairness counts for all members."""
    members = session.query(TeamMemberDB).all()
    result = []
    
    # Get assignments from last 90 days
    from datetime import timedelta
    cutoff_date = date.today() - timedelta(days=90)
    
    for member in members:
        counts = {}
        total = 0
        for task_type in TaskType:
            # Count assignments in the last 90 days
            assignment_count = session.query(AssignmentDB).filter(
                AssignmentDB.member_id == member.id,
                AssignmentDB.task_type == task_type.value,
                AssignmentDB.assignment_date >= cutoff_date
            ).count()
            counts[task_type.value] = assignment_count
            total += assignment_count
        
        result.append({
            "member_id": member.id,
            "member_name": member.name,
            "counts": counts,
            "total": total
        })
    
    return result

@app.get("/api/fairness/export/pdf")
async def export_fairness_pdf(session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Export fairness tracking data to PDF."""
    members = session.query(TeamMemberDB).all()
    fairness_data = []
    
    # Get assignments from last 90 days
    from datetime import timedelta
    cutoff_date = date.today() - timedelta(days=90)
    
    for member in members:
        counts = {}
        total = 0
        for task_type in TaskType:
            # Count assignments in the last 90 days
            assignment_count = session.query(AssignmentDB).filter(
                AssignmentDB.member_id == member.id,
                AssignmentDB.task_type == task_type,
                AssignmentDB.assignment_date >= cutoff_date
            ).count()
            counts[task_type.value] = assignment_count
            total += assignment_count
        
        fairness_data.append({
            "member_id": member.id,
            "member_name": member.name,
            "counts": counts,
            "total": total
        })
    
    file_path = f"out/fairness_{date.today().isoformat()}.pdf"
    export_fairness_to_pdf(fairness_data, file_path)
    return FileResponse(file_path, media_type="application/pdf", filename=f"fairness_{date.today().isoformat()}.pdf")

# Configuration
@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    try:
        config = SchedulingConfig.from_yaml("data/config.yaml")
        return {
            "timezone": config.timezone,
            "fairness_window_days": config.fairness_window_days,
            "atm": {
                "rest_rule_enabled": config.atm_rest_rule_enabled,
                "b_cooldown_days": config.atm_b_cooldown_days,
                "windows": {
                    "morning": {
                        "start": config.atm_morning_window_start.strftime("%H:%M"),
                        "end": config.atm_morning_window_end.strftime("%H:%M")
                    },
                    "midday": {
                        "start": config.atm_midday_window_start.strftime("%H:%M"),
                        "end": config.atm_midday_window_end.strftime("%H:%M")
                    },
                    "night": {
                        "start": config.atm_night_window_start.strftime("%H:%M"),
                        "end": config.atm_night_window_end.strftime("%H:%M")
                    }
                }
            },
            "sysaid": {
                "week_start_day": config.sysaid_week_start_day
            }
        }
    except Exception as e:
        return {"error": str(e)}

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        print("Initializing database...")
        db.create_tables()
        print("Database initialized successfully")
    except Exception as e:
        import traceback
        print(f"ERROR: Failed to initialize database: {e}")
        traceback.print_exc()
        # Don't raise - let the app start but API calls will fail with clear errors

# Task Types CRUD
class ShiftDefModel(BaseModel):
    label: str
    start_time: str
    end_time: str
    required_count: int = 1

class TaskTypeDefCreate(BaseModel):
    name: str
    recurrence: str
    required_count: int = 1
    role_labels: List[str] = []
    rules_json: Optional[dict] = None
    shifts: List[ShiftDefModel] = []

@app.get("/api/task-types")
async def list_task_types(session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = session.query(TaskTypeDef).all()
    result = []
    for t in items:
        shifts = session.query(ShiftDef).filter(ShiftDef.task_type_id == t.id).all()
        result.append({
            "id": t.id,
            "name": t.name,
            "recurrence": t.recurrence,
            "required_count": t.required_count,
            "role_labels": t.role_labels or [],
            "rules_json": json.loads(t.rules_json) if t.rules_json else None,
            "shifts": [
                {"id": s.id, "label": s.label, "start_time": s.start_time, "end_time": s.end_time, "required_count": s.required_count}
                for s in shifts
            ]
        })
    return result

@app.post("/api/task-types")
async def create_task_type(payload: TaskTypeDefCreate, session: Session = Depends(get_db), admin: User = Depends(require_admin)):
    t = TaskTypeDef(
        name=payload.name,
        recurrence=payload.recurrence,
        required_count=payload.required_count,
        role_labels=payload.role_labels,
        rules_json=json.dumps(payload.rules_json) if payload.rules_json else None
    )
    session.add(t)
    session.flush()
    
    for sh in payload.shifts:
        s = ShiftDef(
            task_type_id=t.id,
            label=sh.label,
            start_time=sh.start_time,
            end_time=sh.end_time,
            required_count=sh.required_count
        )
        session.add(s)
    session.commit()
    return {"id": t.id}

@app.delete("/api/task-types/{task_type_id}")
async def delete_task_type(task_type_id: int, session: Session = Depends(get_db), admin: User = Depends(require_admin)):
    session.query(ShiftDef).filter(ShiftDef.task_type_id == task_type_id).delete()
    session.query(TaskTypeDef).filter(TaskTypeDef.id == task_type_id).delete()
    session.commit()
    return {"message": "Deleted"}

class TaskTypeDefUpdate(TaskTypeDefCreate):
    pass

@app.put("/api/task-types/{task_type_id}")
async def update_task_type(task_type_id: int, payload: TaskTypeDefUpdate, session: Session = Depends(get_db), admin: User = Depends(require_admin)):
    t = session.query(TaskTypeDef).filter(TaskTypeDef.id == task_type_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Not found")
    session.query(ShiftDef).filter(ShiftDef.task_type_id == t.id).delete()
    t.name = payload.name
    t.recurrence = payload.recurrence
    t.required_count = payload.required_count
    t.role_labels = payload.role_labels
    t.rules_json = json.dumps(payload.rules_json) if payload.rules_json else None
    session.flush()
    for sh in payload.shifts:
        s = ShiftDef(task_type_id=t.id, label=sh.label, start_time=sh.start_time, end_time=sh.end_time, required_count=sh.required_count)
        session.add(s)
    session.commit()
    return {"message": "Updated"}
    session.query(ShiftDef).filter(ShiftDef.task_type_id == task_type_id).delete()
    session.query(TaskTypeDef).filter(TaskTypeDef.id == task_type_id).delete()
    session.commit()
    return {"message": "Deleted"}

# Swaps
class SwapRequestCreate(BaseModel):
    assignment_id: int
    proposed_member_id: str
    reason: Optional[str] = None

class SwapPeerDecision(BaseModel):
    accept: bool
    note: Optional[str] = None

@app.post("/api/swaps")
async def propose_swap(payload: SwapRequestCreate, session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user.member_id:
        raise HTTPException(status_code=403, detail="Only team members can propose swaps")

    assignment = session.query(AssignmentDB).filter(AssignmentDB.id == payload.assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.member_id != user.member_id:
        raise HTTPException(status_code=403, detail="You can only propose swaps for your own assignments")

    if payload.proposed_member_id == user.member_id:
        raise HTTPException(status_code=400, detail="Cannot swap with yourself")

    swap = SwapRequest(
        assignment_id=payload.assignment_id,
        requested_by=user.member_id,
        proposed_member_id=payload.proposed_member_id,
        reason=payload.reason,
        status="pending_peer"
    )
    session.add(swap)
    session.commit()
    session.refresh(swap)
    return {"id": swap.id, "status": swap.status}


@app.get("/api/swaps")
async def list_swaps(session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    swaps = session.query(SwapRequest).all()
    outgoing = []
    incoming = []
    admin_pending = []

    for swap in swaps:
        data = _serialize_swap(swap)
        if user.member_id and swap.requested_by == user.member_id:
            outgoing.append(data)
        if user.member_id and swap.proposed_member_id == user.member_id and swap.status == "pending_peer":
            incoming.append(data)
        if user.role == "admin" and swap.status == "pending_admin":
            admin_pending.append(data)

    return {
        "outgoing": outgoing,
        "incoming": incoming,
        "admin_pending": admin_pending
    }


@app.post("/api/swaps/{swap_id}/respond")
async def respond_swap(swap_id: int, payload: SwapPeerDecision, session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user.member_id:
        raise HTTPException(status_code=403, detail="Only team members can respond to swaps")
    swap = session.query(SwapRequest).filter(SwapRequest.id == swap_id).first()
    if not swap:
        raise HTTPException(status_code=404, detail="Swap not found")
    if swap.proposed_member_id != user.member_id:
        raise HTTPException(status_code=403, detail="Not authorized for this swap")
    if swap.status != "pending_peer":
        raise HTTPException(status_code=400, detail="Swap is not awaiting your response")

    swap.peer_decision = "accepted" if payload.accept else "rejected"
    swap.peer_decided_at = datetime.now()
    if payload.accept:
        swap.status = "pending_admin"
    else:
        swap.status = "rejected"
        swap.decided_at = datetime.now()
    session.commit()
    return {"message": "Swap updated", "swap": _serialize_swap(swap)}

@app.post("/api/swaps/{swap_id}/decision")
async def decide_swap(swap_id: int, approve: bool, session: Session = Depends(get_db), admin: User = Depends(require_admin)):
    swap = session.query(SwapRequest).filter(SwapRequest.id == swap_id).first()
    if not swap:
        raise HTTPException(status_code=404, detail="Swap not found")
    if swap.status != "pending_admin":
        raise HTTPException(status_code=400, detail="Swap is not awaiting admin decision")
    swap.status = "approved" if approve else "rejected"
    swap.decided_at = datetime.now()
    
    # Apply change if approved and proposed member exists
    if approve and swap.proposed_member_id:
        assignment = session.query(AssignmentDB).filter(AssignmentDB.id == swap.assignment_id).first()
        if assignment:
            assignment.member_id = swap.proposed_member_id
    
    session.commit()
    return {"swap": _serialize_swap(swap)}

# Update assignment (manual edit)
class AssignmentUpdate(BaseModel):
    member_id: str

@app.patch("/api/assignments/{assignment_id}")
async def update_assignment(assignment_id: int, payload: AssignmentUpdate, session: Session = Depends(get_db), admin: User = Depends(require_admin)):
    assignment = session.query(AssignmentDB).filter(AssignmentDB.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    member = session.query(TeamMemberDB).filter(TeamMemberDB.id == payload.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    assignment.member_id = payload.member_id
    session.commit()
    return {"message": "Assignment updated"}

# Exports: Excel/PDF
@app.get("/api/schedules/{schedule_id}/export/excel")
async def export_schedule_excel(schedule_id: int, session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Export schedule to Excel format."""
    schedule = session.query(ScheduleDB).filter(ScheduleDB.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Build schedule model
    db_members = session.query(TeamMemberDB).all()
    members_dict = {m.id: db_member_to_model(m, session) for m in db_members}
    
    assignments = session.query(AssignmentDB).filter(
        AssignmentDB.schedule_id == schedule_id
    ).all()
    
    schedule_assignments = []
    for a in assignments:
        member = members_dict.get(a.member_id)
        if member:
            assignment = Assignment(
                task_type=a.task_type,
                assignee=member,
                date=a.assignment_date,
                week_start=a.week_start,
                shift_label=a.shift_label
            )
            schedule_assignments.append(assignment)
    
    schedule_obj = Schedule(
        assignments=schedule_assignments,
        start_date=schedule.start_date,
        end_date=schedule.end_date
    )
    
    file_path = f"out/schedule_{schedule_id}.xlsx"
    export_to_excel(schedule_obj, file_path)
    return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=f"schedule_{schedule_id}.xlsx")

@app.get("/api/schedules/{schedule_id}/export/pdf")
async def export_schedule_pdf(schedule_id: int, session: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Export schedule to PDF format."""
    schedule = session.query(ScheduleDB).filter(ScheduleDB.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Build schedule model
    db_members = session.query(TeamMemberDB).all()
    members_dict = {m.id: db_member_to_model(m, session) for m in db_members}
    
    assignments = session.query(AssignmentDB).filter(
        AssignmentDB.schedule_id == schedule_id
    ).all()
    
    schedule_assignments = []
    for a in assignments:
        member = members_dict.get(a.member_id)
        if member:
            assignment = Assignment(
                task_type=a.task_type,
                assignee=member,
                date=a.assignment_date,
                week_start=a.week_start,
                shift_label=a.shift_label
            )
            schedule_assignments.append(assignment)
    
    schedule_obj = Schedule(
        assignments=schedule_assignments,
        start_date=schedule.start_date,
        end_date=schedule.end_date
    )
    
    file_path = f"out/schedule_{schedule_id}.pdf"
    export_to_pdf(schedule_obj, file_path)
    return FileResponse(file_path, media_type="application/pdf", filename=f"schedule_{schedule_id}.pdf")


