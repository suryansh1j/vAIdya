"""
Full NLP processing pipeline: transcription, symptom extraction, and
patient info extraction.

Requires the optional ML dependencies (see requirements-ml.txt). Import this
module only through backend.nlp_processor, which falls back gracefully when
these dependencies are not installed.
"""
import csv
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

# On Windows, HuggingFace's cache uses symlinks by default, which raise
# "OSError: [WinError 1314] A required privilege is not held" unless Developer
# Mode or admin is enabled. Disabling symlinks makes it copy files instead.
# This must run before huggingface_hub is imported (pulled in below by
# faster_whisper / transformers), so it stays at the top of the module.
if os.name == "nt":
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")

import spacy
import torch
from faster_whisper import WhisperModel
from transformers import AutoModelForQuestionAnswering, AutoTokenizer
from negspacy.negation import Negex  # noqa: F401 — registers the "negex" spaCy factory

from .config import settings
from .logger import logger


class AudioTranscriber:
    """Handles audio transcription using faster-whisper."""

    def __init__(self):
        self.model = WhisperModel(
            settings.WHISPER_MODEL,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE
        )
        logger.info(f"Loaded Whisper model: {settings.WHISPER_MODEL}")

    def transcribe(self, audio_path: Path) -> str:
        """
        Transcribe an audio file to text.

        faster-whisper decodes m4a/wav/mp3/ogg directly (via PyAV) and
        handles long audio internally, so no format conversion or manual
        chunking is needed.
        """
        logger.info(f"Starting transcription of {audio_path}")

        segments, _ = self.model.transcribe(str(audio_path), language="en")
        transcript = "".join(segment.text for segment in segments).strip()

        logger.info(f"Transcription complete: {len(transcript)} characters")
        return transcript


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

    QA_MODEL = "distilbert-base-cased-distilled-squad"

    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        # Use the model directly rather than pipeline("question-answering"):
        # transformers v5 removed that high-level task, and the model classes
        # work across v4 and v5.
        self.qa_tokenizer = AutoTokenizer.from_pretrained(self.QA_MODEL)
        self.qa_model = AutoModelForQuestionAnswering.from_pretrained(self.QA_MODEL)
        self.qa_model.eval()
        logger.info("Patient info extractor initialized")

    def _answer_question(self, question: str, context: str) -> str:
        """Run extractive QA and return the best answer span (empty if none)."""
        inputs = self.qa_tokenizer(
            question, context,
            return_tensors="pt", truncation="only_second", max_length=384,
        )
        with torch.no_grad():
            outputs = self.qa_model(**inputs)

        start_logits = outputs.start_logits[0].clone()
        end_logits = outputs.end_logits[0].clone()

        # Restrict the answer span to context tokens (sequence id 1); mask out
        # the question and special tokens so the answer can't come from them.
        seq_ids = inputs.sequence_ids(0)
        for i, sid in enumerate(seq_ids):
            if sid != 1:
                start_logits[i] = float("-inf")
                end_logits[i] = float("-inf")

        start = int(torch.argmax(start_logits))
        end = int(torch.argmax(end_logits))
        if end < start:
            return ""

        answer_ids = inputs["input_ids"][0][start:end + 1]
        return self.qa_tokenizer.decode(answer_ids, skip_special_tokens=True).strip()

    def extract(self, transcript: str) -> Dict[str, Optional[str]]:
        """
        Extract patient information from transcript.

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
                    answer = self._answer_question(question, transcript)
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
        Process audio file through the complete NLP pipeline.

        Returns:
            Dictionary containing transcript, symptoms, and patient info
        """
        logger.info(f"Starting NLP pipeline for {audio_path}")

        transcript = self.transcriber.transcribe(audio_path)
        symptoms = self.symptom_extractor.extract(transcript)
        patient_info = self.patient_info_extractor.extract(transcript)

        logger.info("NLP pipeline complete")

        return {
            "transcript": transcript,
            "symptoms": symptoms,
            "patient_info": patient_info
        }
