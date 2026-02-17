"""
NLP processing module - STUB VERSION for deployment without heavy dependencies.
This version allows the app to deploy and run, but NLP features are disabled.

TODO: Replace with full implementation once deployment issues are resolved.
"""
import os
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .config import settings
from .logger import logger


class AudioTranscriber:
    """Stub: Audio transcription disabled."""
    
    def __init__(self):
        logger.warning("AudioTranscriber: Using stub implementation - transcription disabled")
    
    def transcribe(self, audio_path: Path) -> str:
        """
        Stub transcription - returns placeholder text.
        """
        logger.warning(f"Transcription requested for {audio_path} but feature is disabled (stub)")
        return "[Transcription feature temporarily disabled - awaiting deployment fix]"


class SymptomExtractor:
    """Stub: Symptom extraction disabled."""
    
    def __init__(self):
        logger.warning("SymptomExtractor: Using stub implementation - extraction disabled")
    
    def extract(self, transcript: str) -> Dict[str, List[str]]:
        """
        Stub extraction - returns empty results.
        """
        logger.warning("Symptom extraction requested but feature is disabled (stub)")
        return {
            "affirmed": [],
            "negated": []
        }


class PatientInfoExtractor:
    """Stub: Patient info extraction disabled."""
    
    def __init__(self):
        logger.warning("PatientInfoExtractor: Using stub implementation - extraction disabled")
    
    def extract(self, transcript: str) -> Dict[str, Optional[str]]:
        """
        Stub extraction - returns empty patient info.
        """
        logger.warning("Patient info extraction requested but feature is disabled (stub)")
        return {
            "PatientName": None,
            "Age": None,
            "Gender": None,
            "ChiefComplaint": None,
            "PastMedicalHistory": None,
            "FamilyHistory": None,
            "PreviousSurgeries": None,
            "Lifestyle": None,
            "Allergies": None,
            "CurrentMedications": None,
        }


class NLPPipeline:
    """Stub NLP processing pipeline."""
    
    def __init__(self):
        logger.warning("NLPPipeline: Using stub implementation - NLP features disabled")
        self.transcriber = AudioTranscriber()
        self.symptom_extractor = SymptomExtractor()
        self.patient_info_extractor = PatientInfoExtractor()
    
    def process(self, audio_path: Path) -> Dict:
        """
        Stub processing - returns placeholder results.
        """
        logger.warning(f"NLP pipeline requested for {audio_path} but features are disabled (stub)")
        
        transcript = self.transcriber.transcribe(audio_path)
        symptoms = self.symptom_extractor.extract(transcript)
        patient_info = self.patient_info_extractor.extract(transcript)
        
        result = {
            "transcript": transcript,
            "symptoms": symptoms,
            "patient_info": patient_info
        }
        
        return result
