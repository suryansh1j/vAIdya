"""
vAIdya - AI Assistant for Medical Audio & Diagnostic Notes
Main FastAPI application with authentication, database, and NLP processing.
"""
import json
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from .auth import create_access_token, decode_access_token, get_password_hash, verify_password
from .config import settings
from .database import get_db, init_db
from .logger import logger
from .models import Patient, User
from .nlp_processor import NLP_AVAILABLE, NLPPipeline

# Pydantic Models
class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    # bcrypt operates on at most 72 bytes of input
    password: str = Field(min_length=8, max_length=72)
    full_name: Optional[str] = Field(default=None, max_length=255)


class PatientUpdate(BaseModel):
    """Editable patient fields; only the fields present in the request are updated."""
    patient_name: Optional[str] = Field(default=None, max_length=255)
    age: Optional[str] = Field(default=None, max_length=10)
    gender: Optional[str] = Field(default=None, max_length=20)
    chief_complaint: Optional[str] = None
    past_medical_history: Optional[str] = None
    family_history: Optional[str] = None
    previous_surgeries: Optional[str] = None
    lifestyle: Optional[str] = None
    allergies: Optional[str] = None
    current_medications: Optional[str] = None


# ==================== Lifespan ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application on startup, cleanup on shutdown."""
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"NLP pipeline available: {NLP_AVAILABLE}")

    init_db()
    logger.info("Database initialized")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI Assistant for Medical Audio & Diagnostic Notes",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# NLP pipeline singleton (lazy, thread-safe)
nlp_pipeline: Optional[NLPPipeline] = None
_nlp_pipeline_lock = threading.Lock()

def get_nlp_pipeline() -> NLPPipeline:
    """Get or create the NLP pipeline instance (thread-safe lazy init)."""
    global nlp_pipeline
    if nlp_pipeline is None:
        with _nlp_pipeline_lock:
            if nlp_pipeline is None:
                logger.info("Initializing NLP pipeline...")
                nlp_pipeline = NLPPipeline()
    return nlp_pipeline


# ==================== Rate Limiting ====================

class RateLimiter:
    """Simple in-memory sliding-window rate limiter keyed by client IP.

    Suitable for a single-process deployment; swap for a shared store
    (e.g. Redis) if scaling to multiple instances.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()

        with self._lock:
            hits = self._hits[client_ip]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()

            if len(hits) >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                )

            hits.append(now)


login_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
register_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)


# ==================== Authentication ====================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    return user


@app.post("/api/v1/auth/register", dependencies=[Depends(register_rate_limiter)])
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"New user registered: {user_data.username}")

    return {
        "message": "User registered successfully",
        "username": user_data.username,
        "email": user_data.email
    }


@app.post("/api/v1/auth/login", dependencies=[Depends(login_rate_limiter)])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token. Accepts either username or email in the username field."""
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )

    logger.info(f"User logged in: {user.username}")

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get("/api/v1/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_doctor": current_user.is_doctor
    }


# ==================== Audio Processing ====================

def validate_audio_file(file: UploadFile) -> None:
    """Validate uploaded audio file extension."""
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in settings.ALLOWED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format. Allowed formats: {', '.join(settings.ALLOWED_AUDIO_FORMATS)}"
        )


async def save_upload_with_limit(file: UploadFile, dest: Path) -> None:
    """Stream the upload to disk, enforcing the size limit while writing.

    The declared Content-Length can be absent or wrong, so the limit is
    enforced on actual bytes received.
    """
    chunk_size = 1024 * 1024  # 1MB
    bytes_written = 0

    with open(dest, "wb") as buffer:
        while chunk := await file.read(chunk_size):
            bytes_written += len(chunk)
            if bytes_written > settings.MAX_UPLOAD_SIZE_BYTES:
                buffer.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Maximum size: {settings.max_upload_size_display}"
                )
            buffer.write(chunk)


@app.post("/api/v1/upload-audio")
async def upload_audio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process audio file.
    Returns extracted patient information.
    """
    logger.info(f"Audio upload request from user: {current_user.username}")

    if not NLP_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audio processing is temporarily unavailable on this deployment. "
                   "The ML dependencies are not installed."
        )

    # Validate file
    validate_audio_file(file)

    # Generate unique filename
    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    audio_path = settings.AUDIO_DIR / unique_filename

    try:
        await save_upload_with_limit(file, audio_path)
        logger.info(f"Audio file saved: {unique_filename}")

        # Process through NLP pipeline
        pipeline = get_nlp_pipeline()
        result = pipeline.process(audio_path)

        # Save to database
        patient = Patient(
            doctor_id=current_user.id,
            patient_name=result["patient_info"].get("PatientName"),
            age=result["patient_info"].get("Age"),
            gender=result["patient_info"].get("Gender"),
            chief_complaint=result["patient_info"].get("ChiefComplaint"),
            past_medical_history=result["patient_info"].get("PastMedicalHistory"),
            family_history=result["patient_info"].get("FamilyHistory"),
            previous_surgeries=result["patient_info"].get("PreviousSurgeries"),
            lifestyle=result["patient_info"].get("Lifestyle"),
            allergies=result["patient_info"].get("Allergies"),
            current_medications=result["patient_info"].get("CurrentMedications"),
            audio_filename=unique_filename,
            transcript_text=result["transcript"],
            symptoms_extracted=json.dumps(result["symptoms"])
        )

        db.add(patient)
        db.commit()
        db.refresh(patient)

        logger.info(f"Patient record created: ID {patient.id}")

        return {
            "patient_id": patient.id,
            "patient_info": result["patient_info"],
            "symptoms": result["symptoms"],
            "transcript": result["transcript"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio processing failed: {str(e)}", exc_info=True)

        # Cleanup audio file on error
        audio_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Audio processing failed. Please try again or contact support."
        )


# ==================== Patient Management ====================

def parse_symptoms(raw: Optional[str]) -> dict:
    """Parse the stored symptoms JSON, tolerating legacy str(dict) rows."""
    if not raw:
        return {"affirmed": [], "negated": []}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        # Legacy rows were stored with str(dict) (single quotes) — not valid
        # JSON; return them as-is so the data is still visible.
        return {"raw": raw}


@app.get("/api/v1/patients")
async def get_patients(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: Optional[str] = Query(default=None, max_length=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get patients for the current doctor (paginated, newest first).

    Optional q searches name, chief complaint, and transcript.
    """
    base_query = db.query(Patient).filter(Patient.doctor_id == current_user.id)

    if q:
        pattern = f"%{q}%"
        base_query = base_query.filter(
            Patient.patient_name.ilike(pattern)
            | Patient.chief_complaint.ilike(pattern)
            | Patient.transcript_text.ilike(pattern)
        )

    total = base_query.count()
    patients = (
        base_query
        .order_by(Patient.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "count": total,
        "limit": limit,
        "offset": offset,
        "patients": [
            {
                "id": p.id,
                "patient_name": p.patient_name,
                "age": p.age,
                "gender": p.gender,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in patients
        ]
    }


@app.get("/api/v1/patients/{patient_id}")
async def get_patient(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed patient information."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.doctor_id == current_user.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    return {
        "id": patient.id,
        "patient_name": patient.patient_name,
        "age": patient.age,
        "gender": patient.gender,
        "chief_complaint": patient.chief_complaint,
        "past_medical_history": patient.past_medical_history,
        "family_history": patient.family_history,
        "previous_surgeries": patient.previous_surgeries,
        "lifestyle": patient.lifestyle,
        "allergies": patient.allergies,
        "current_medications": patient.current_medications,
        "transcript": patient.transcript_text,
        "symptoms": parse_symptoms(patient.symptoms_extracted),
        "created_at": patient.created_at.isoformat() if patient.created_at else None
    }


@app.patch("/api/v1/patients/{patient_id}")
async def update_patient(
    patient_id: int,
    update: PatientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update editable fields of a patient record (doctor notes edits)."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.doctor_id == current_user.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    changes = update.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)

    logger.info(f"Patient {patient_id} updated by {current_user.username} ({len(changes)} fields)")

    return {"message": "Patient updated", "id": patient.id, "updated_fields": sorted(changes)}


@app.delete("/api/v1/patients/{patient_id}")
async def delete_patient(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a patient record and its stored audio file."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.doctor_id == current_user.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    if patient.audio_filename:
        audio_path = settings.AUDIO_DIR / patient.audio_filename
        try:
            audio_path.unlink(missing_ok=True)
        except OSError as e:
            logger.warning(f"Could not delete audio file {patient.audio_filename}: {e}")

    db.delete(patient)
    db.commit()

    logger.info(f"Patient {patient_id} deleted by {current_user.username}")

    return {"message": "Patient deleted", "id": patient_id}


# ==================== Health Check ====================

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "nlp_available": NLP_AVAILABLE
    }


# ==================== Static Files ====================

# Mount frontend (only in development)
if settings.DEBUG:
    app.mount("/", StaticFiles(directory=str(settings.FRONTEND_DIR), html=True), name="frontend")
    logger.info("Frontend static files mounted")
