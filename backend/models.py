"""
Database models for vAIdya application.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_doctor = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patients = relationship("Patient", back_populates="doctor")
    

class Patient(Base):
    """Patient information model."""
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Patient details
    patient_name = Column(String(255))
    age = Column(String(10))
    gender = Column(String(20))
    
    # Medical information
    chief_complaint = Column(Text)
    past_medical_history = Column(Text)
    family_history = Column(Text)
    previous_surgeries = Column(Text)
    lifestyle = Column(Text)
    allergies = Column(Text)
    current_medications = Column(Text)
    
    # Audio & Transcript
    audio_filename = Column(String(255))
    transcript_text = Column(Text)
    symptoms_extracted = Column(Text)  # JSON string
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    doctor = relationship("User", back_populates="patients")
