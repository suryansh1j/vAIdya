import re
import spacy
from transformers import pipeline
import os
import json

# Load spaCy English small model
nlp = spacy.load("en_core_web_sm")

# Initialize HuggingFace DistilBERT QA pipeline for question answering
qa = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")

def get_nearest_line_with_keyword(transcript, keywords):
    """Return the first line containing any of the keywords."""
    for line in transcript.splitlines():
        if any(k.lower() in line.lower() for k in keywords):
            return line.strip()
    return None

def extract_medications(text):
    """Split medications list on commas, and conjunctions."""
    if not text:
        return []
    meds_list = re.split(r',| and | & ', text, flags=re.IGNORECASE)
    meds = [med.strip(" .;:") for med in meds_list if med.strip()]
    return meds

def improve_family_history_extraction(transcript):
    """Extract detailed Family History lines matching medical family-related terms."""
    pattern = r'(?i)(family history[^.\n]*|father[^.\n]*|mother[^.\n]*|sibling[^.\n]*|brother[^.\n]*|sister[^.\n]*)'
    matches = re.findall(pattern, transcript)
    if matches:
        # Combine unique matches into single string
        return " ".join(sorted(set(matches), key=matches.index))
    return "None"

def clean_answer(ans, remove_phrases=[]):
    """Remove unwanted phrases and trim whitespace/punctuation."""
    if not ans:
        return ans
    ans_clean = ans.strip(" .\n\t?")
    for phrase in remove_phrases:
        phrase_lower = phrase.lower().strip(" .\n\t?")
        ans_lower = ans_clean.lower()
        if ans_lower.startswith(phrase_lower):
            ans_clean = ans_clean[len(phrase_lower):].strip(" .\n\t?")
    ans_clean = ans_clean.rstrip("?").strip()
    return ans_clean

def is_bad_answer(ans, field):
    """Check if an answer is likely invalid or uninformative."""
    if not ans:
        return True
    bads = ["years old", "none", "nothing", "not mentioned", "no", "n/a", "any", "unknown"]
    ans_lower = ans.lower()
    if field != "Age" and any(bad in ans_lower for bad in bads):
        return True
    # Age field can be numeric, treat as good answer
    if field != "ChiefComplaint" and len(ans) < 3:
        return True
    return False

def extract_patient_info_refined(transcript_text):
    """Extract multiple structured fields from patient transcript text."""
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

    # --- Extract Patient Name using spaCy PERSON entities ---
    doc = nlp(transcript_text)
    persons = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]
    if persons:
        # Prefer first person entity, clean common titles/prefixes if needed
        name = persons[0]
        # Remove common prefixes if exist
        name = re.sub(r"^(mr|mrs|miss|ms|dr|prof)\.?\s+", "", name, flags=re.I)
        info["PatientName"] = name

    # --- Extract Gender using regex for common gender terms ---
    gender_match = re.search(r'\b(male|female|man|woman|boy|girl)\b', transcript_text, re.I)
    if gender_match:
        gender_lookup = {
            "male": "Male", "man": "Male", "boy": "Male",
            "female": "Female", "woman": "Female", "girl": "Female"
        }
        gender_key = gender_match.group(1).lower()
        info["Gender"] = gender_lookup.get(gender_key, gender_key.capitalize())

    # --- Extract Age using multiple regex patterns ---
    age_patterns = [
        r'(\d{1,3})\s*[-–—]?\s*year[s]?\s*old',
        r'aged\s*(\d{1,3})',
        r'(\d{1,3})\s*y/o',
        r'(\d{1,3})\s*years\s*of\s*age',
        r'(\d{1,3})\s*yo\b',
        r'(\d{1,3})\s*years?'
    ]
    for pattern in age_patterns:
        match = re.search(pattern, transcript_text, re.I)
        if match:
            age_candidate = next((g for g in match.groups() if g and g.isdigit()), None)
            if age_candidate:
                info['Age'] = age_candidate
                break

    # --- Define questions per field for QA extraction ---
    questions = {
        "ChiefComplaint": ["What is the patient's main complaint?", "Why did the patient come today?"],
        "PastMedicalHistory": ["What is the patient's past medical history?", "Has the patient had any prior illnesses?"],
        "FamilyHistory": ["What is the patient's family history?", "Describe the patient's family illnesses."],
        "PreviousSurgeries": ["Has the patient had any previous surgeries?", "What surgeries has the patient undergone?"],
        "Lifestyle": ["Describe the patient's lifestyle.", "Does the patient smoke or drink?"],
        "Allergies": ["What allergies does the patient have?", "Is the patient allergic to any medication or substance?"],
        "CurrentMedications": ["What medications is the patient currently taking?", "Which drugs does the patient take?"],
    }

    # Phrases to remove from answers for each field (improve cleanliness)
    removal_phrases = {
        "FamilyHistory": [
            "any family history of illnesses",
            "what is the patient's family history",
            "describe the patient's family illnesses",
            "family history of illnesses"
        ],
        "PreviousSurgeries": [
            "has the patient had any previous surgeries",
            "what surgeries has the patient undergone"
        ],
        "Lifestyle": [
            "describe the patient's lifestyle",
            "does the patient smoke or drink"
        ],
        "Allergies": [
            "what allergies does the patient have",
            "is the patient allergic to any medication or substance"
        ],
        "CurrentMedications": [
            "what medications is the patient currently taking",
            "which drugs does the patient take"
        ],
        "ChiefComplaint": [
            "what is the patient's main complaint",
            "why did the patient come today"
        ],
        "PastMedicalHistory": [
            "what is the patient's past medical history",
            "has the patient had any prior illnesses"
        ]
    }

    for field, question_list in questions.items():
        answer_text = None
        # Try each question on the transcript using the QA pipeline
        for question in question_list:
            try:
                result = qa(question=question, context=transcript_text)
                ans = result.get('answer', '').strip()
                ans = clean_answer(ans, removal_phrases.get(field, []))
                if ans and not is_bad_answer(ans, field):
                    answer_text = ans
                    break
            except Exception:
                continue

        # Special handling for family history if empty or negative answers
        if field == "FamilyHistory":
            if not answer_text or answer_text.lower() in ['none', 'no', '']:
                answer_text = improve_family_history_extraction(transcript_text)

        # Split medications list cleanly
        if field == "CurrentMedications" and answer_text:
            meds = extract_medications(answer_text)
            answer_text = ', '.join(meds)

        # If no answer yet, fallback to line nearest keyword hit
        if not answer_text:
            keywords = [field.replace("History", " history")
                              .replace("ChiefComplaint", "complaint")
                              .replace("CurrentMedications", "medication")
                              .replace("PreviousSurgeries", "surgery")
                              .replace("PastMedicalHistory", "illness").lower()]
            fallback = get_nearest_line_with_keyword(transcript_text, keywords)
            if fallback:
                fallback = clean_answer(fallback, removal_phrases.get(field, []))
                if field == "CurrentMedications":
                    meds = extract_medications(fallback)
                    fallback = ', '.join(meds)
                answer_text = fallback

        if answer_text:
            info[field] = answer_text

    return info

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    transcript_path = os.path.join(BASE_DIR, "transcripts", "full_transcript.txt")

    if not os.path.exists(transcript_path):
        raise FileNotFoundError(f"Transcript not found at {transcript_path}")

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()

    results = extract_patient_info_refined(transcript)

    output_path = os.path.join(BASE_DIR, "transcripts", "patient_info.json")
    with open(output_path, "w", encoding="utf-8") as out_f:
        json.dump(results, out_f, indent=2, ensure_ascii=False)

    print(f"[INFO] Patient info saved to {output_path}\n")
    for field, value in results.items():
        print(f"{field}: {value}\n")
