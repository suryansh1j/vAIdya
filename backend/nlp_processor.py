"""
NLP processing module - refactored for direct import instead of subprocess.
Combines transcription, symptom extraction, and patient info extraction.
"""
import os
import json
import re
import spacy
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from faster_whisper import WhisperModel
from pydub import AudioSegment
from transformers import pipeline
from spacy.pipeline import EntityRuler
from negspacy.negation import Negex
import csv

from .config import settings
from .logger import logger


class AudioTranscriber:
    """Handles audio transcription using Whisper."""
    
    def __init__(self):
        self.model = WhisperModel(
            settings.WHISPER_MODEL,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE
        )
        logger.info(f"Loaded Whisper model: {settings.WHISPER_MODEL}")
    
    def transcribe(self, audio_path: Path) -> str:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcribed text
        """
        logger.info(f"Starting transcription of {audio_path}")
        
        # Convert to WAV if needed
        wav_path = audio_path.with_suffix('.wav')
        if audio_path.suffix.lower() != '.wav':
            logger.debug(f"Converting {audio_path} to WAV format")
            sound = AudioSegment.from_file(str(audio_path))
            sound.export(str(wav_path), format="wav")
        else:
            wav_path = audio_path
        
        # Load and chunk audio
        audio = AudioSegment.from_file(str(wav_path))
        duration_ms = len(audio)
        chunk_length_ms = settings.AUDIO_CHUNK_LENGTH_SECONDS * 1000
        
        full_transcript = ""
        
        # Process chunks
        for start_ms in range(0, duration_ms, chunk_length_ms):
            end_ms = min(start_ms + chunk_length_ms, duration_ms)
            chunk = audio[start_ms:end_ms]
            
            # Export chunk
            chunk_path = wav_path.parent / "temp_chunk.wav"
            chunk.export(str(chunk_path), format="wav")
            
            logger.debug(f"Transcribing chunk {start_ms//1000}s to {end_ms//1000}s")
            
            try:
                segments, _ = self.model.transcribe(str(chunk_path), language="en")
                chunk_text = ''.join([seg.text for seg in segments])
                full_transcript += chunk_text + " "
            except Exception as e:
                logger.error(f"Failed to transcribe chunk: {e}")
                continue
            finally:
                # Cleanup chunk
                if chunk_path.exists():
                    chunk_path.unlink()
        
        # Cleanup WAV if it was converted
        if wav_path != audio_path and wav_path.exists():
            wav_path.unlink()
        
        logger.info(f"Transcription complete: {len(full_transcript)} characters")
        return full_transcript.strip()


class SymptomExtractor:
    """Extracts and categorizes symptoms from medical transcripts."""
    
    def __init__(self):
        # Load symptom mapping
        mapping_path = settings.BASE_DIR / "terms" / "full_symptom_mapping.json"
        with open(mapping_path, encoding='utf-8') as f:
            self.term_mapping = json.load(f)
        
        # Setup NLP pipeline
        self.nlp = spacy.load("en_core_web_sm", disable=["ner"])
        self.nlp.add_pipe("sentencizer")
        
        # Add entity ruler
        ruler = self.nlp.add_pipe("entity_ruler", config={"phrase_matcher_attr": "LOWER"})
        
        # Load patterns from CSV
        patterns = []
        csv_path = settings.BASE_DIR / "terms" / "full_symptom_mapping.csv"
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                term = row["term"].lower().strip()
                label = row["label"]
                tokens = term.split()
                
                patterns.append({"label": label, "pattern": [{"LOWER": t} for t in tokens]})
                patterns.append({"label": label, "pattern": [{"LEMMA": t} for t in tokens]})
        
        ruler.add_patterns(patterns)
        
        # Add negation detection
        self.nlp.add_pipe("negex", last=True)
        
        logger.info("Symptom extractor initialized")
    
    def extract(self, transcript: str) -> Dict[str, List[str]]:
        """
        Extract symptoms from transcript.
        
        Args:
            transcript: Medical transcript text
            
        Returns:
            Dictionary with 'affirmed' and 'negated' symptom lists
        """
        doc = self.nlp(transcript)
        
        affirmed = []
        negated = []
        
        for ent in doc.ents:
            ent_text = ent.text.lower().strip()
            mapped_term = self.term_mapping.get(ent_text, ent_text)
            
            if ent._.negex:
                negated.append(mapped_term)
            else:
                affirmed.append(mapped_term)
        
        # Remove duplicates while preserving order
        affirmed = list(dict.fromkeys(affirmed))
        negated = list(dict.fromkeys(negated))
        
        logger.info(f"Extracted {len(affirmed)} affirmed and {len(negated)} negated symptoms")
        
        return {
            "affirmed": affirmed,
            "negated": negated
        }


class PatientInfoExtractor:
    """Extracts structured patient information from transcripts."""
    
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.qa = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")
        logger.info("Patient info extractor initialized")
    
    def extract(self, transcript: str) -> Dict[str, Optional[str]]:
        """
        Extract patient information from transcript.
        
        Args:
            transcript: Medical transcript text
            
        Returns:
            Dictionary of extracted patient information
        """
        info = {
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
        
        # Extract name using spaCy NER
        doc = self.nlp(transcript)
        persons = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]
        if persons:
            name = persons[0]
            name = re.sub(r"^(mr|mrs|miss|ms|dr|prof)\.?\s+", "", name, flags=re.I)
            info["PatientName"] = name
        
        # Extract gender
        gender_match = re.search(r'\b(male|female|man|woman|boy|girl)\b', transcript, re.I)
        if gender_match:
            gender_lookup = {
                "male": "Male", "man": "Male", "boy": "Male",
                "female": "Female", "woman": "Female", "girl": "Female"
            }
            info["Gender"] = gender_lookup.get(gender_match.group(1).lower(), 
                                               gender_match.group(1).capitalize())
        
        # Extract age
        age_patterns = [
            r'(\d{1,3})\s*[-–—]?\s*year[s]?\s*old',
            r'aged\s*(\d{1,3})',
            r'(\d{1,3})\s*y/o',
            r'(\d{1,3})\s*years?\s*of\s*age',
            r'(\d{1,3})\s*yo\b',
        ]
        for pattern in age_patterns:
            match = re.search(pattern, transcript, re.I)
            if match:
                info['Age'] = match.group(1)
                break
        
        # Extract other fields using QA
        questions = {
            "ChiefComplaint": ["What is the patient's main complaint?"],
            "PastMedicalHistory": ["What is the patient's past medical history?"],
            "FamilyHistory": ["What is the patient's family history?"],
            "PreviousSurgeries": ["Has the patient had any previous surgeries?"],
            "Lifestyle": ["Describe the patient's lifestyle."],
            "Allergies": ["What allergies does the patient have?"],
            "CurrentMedications": ["What medications is the patient currently taking?"],
        }
        
        for field, question_list in questions.items():
            for question in question_list:
                try:
                    result = self.qa(question=question, context=transcript)
                    answer = result.get('answer', '').strip()
                    if answer and len(answer) > 2:
                        info[field] = answer
                        break
                except Exception as e:
                    logger.debug(f"QA failed for {field}: {e}")
                    continue
        
        logger.info("Patient info extraction complete")
        return info


class NLPPipeline:
    """Complete NLP processing pipeline."""
    
    def __init__(self):
        self.transcriber = AudioTranscriber()
        self.symptom_extractor = SymptomExtractor()
        self.patient_info_extractor = PatientInfoExtractor()
    
    def process(self, audio_path: Path) -> Dict:
        """
        Process audio file through complete NLP pipeline.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary containing transcript, symptoms, and patient info
        """
        logger.info(f"Starting NLP pipeline for {audio_path}")
        
        # Transcribe
        transcript = self.transcriber.transcribe(audio_path)
        
        # Extract symptoms
        symptoms = self.symptom_extractor.extract(transcript)
        
        # Extract patient info
        patient_info = self.patient_info_extractor.extract(transcript)
        
        result = {
            "transcript": transcript,
            "symptoms": symptoms,
            "patient_info": patient_info
        }
        
        logger.info("NLP pipeline complete")
        return result
