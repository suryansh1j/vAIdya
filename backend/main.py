"""
vAIdya - AI Assistant for Medical Audio & Diagnostic Notes
Main FastAPI application with authentication, database, and NLP processing.
"""
import os
import uuid
from pathlib import Path
from typing import Optional
from datetime import timedelta

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .config import settings
from .logger import logger
from .database import init_db, get_db
from .models import User, Patient
from .auth import verify_password, get_password_hash, create_access_token, decode_access_token
from .nlp_processor import NLPPipeline

# Pydantic Models
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI Assistant for Medical Audio & Diagnostic Notes",
    version="1.0.0",
    debug=settings.DEBUG
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

# Initialize NLP pipeline (lazy loading)
nlp_pipeline: Optional[NLPPipeline] = None

def get_nlp_pipeline() -> NLPPipeline:
    """Get or create NLP pipeline instance."""
    global nlp_pipeline
    if nlp_pipeline is None:
        logger.info("Initializing NLP pipeline...")
        nlp_pipeline = NLPPipeline()
    return nlp_pipeline


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




@app.post("/api/v1/auth/register")
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


@app.post("/api/v1/auth/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token."""
    user = db.query(User).filter(User.username == form_data.username).first()
    
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
    """Validate uploaded audio file."""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format. Allowed formats: {', '.join(settings.ALLOWED_AUDIO_FORMATS)}"
        )
    
    # Check file size (if available)
    if hasattr(file, 'size') and file.size:
        if file.size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.max_upload_size_display}"
            )


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
    
    # Validate file
    validate_audio_file(file)
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    audio_path = settings.AUDIO_DIR / unique_filename
    
    try:
        # Save uploaded file
        with open(audio_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
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
            symptoms_extracted=str(result["symptoms"])
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
        
    except Exception as e:
        logger.error(f"Audio processing failed: {str(e)}", exc_info=True)
        
        # Cleanup audio file on error
        if audio_path.exists():
            audio_path.unlink()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio processing failed: {str(e)}"
        )


# ==================== Patient Management ====================

@app.get("/api/v1/patients")
async def get_patients(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all patients for current doctor."""
    patients = db.query(Patient).filter(Patient.doctor_id == current_user.id).all()
    
    return {
        "count": len(patients),
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
        "symptoms": patient.symptoms_extracted,
        "created_at": patient.created_at.isoformat() if patient.created_at else None
    }


# ==================== Health Check ====================

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT
    }


# ==================== Startup & Shutdown ====================

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info(f"Shutting down {settings.APP_NAME}")


# ==================== Static Files ====================

# Mount frontend (only in development)
if settings.DEBUG:
    app.mount("/", StaticFiles(directory=str(settings.FRONTEND_DIR), html=True), name="frontend")
    logger.info("Frontend static files mounted")