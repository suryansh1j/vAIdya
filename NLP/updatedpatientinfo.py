import re
import spacy
from transformers import pipeline
import os
import json

# Load spaCy for NLP tasks
nlp = spacy.load("en_core_web_sm")

# Initialize HuggingFace QA pipeline
qa = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")


# ---- Your function definitions here (get_nearest_line_with_keyword etc.) ----
# ...copy all your functions unchanged from the friend’s code...

def get_nearest_line_with_keyword(transcript, keywords):
    for line in transcript.splitlines():
        if any(k.lower() in line.lower() for k in keywords):
            return line.strip()
    return None


def extract_medications(text):
    if not text:
        return []
    meds_list = re.split(r',| and | & ', text, flags=re.IGNORECASE)
    meds = [med.strip(' .;:') for med in meds_list if med.strip()]
    return meds


def improve_family_history_extraction(transcript):
    pattern = r'(?i)(family history[^.\n]*|father[^.\n]*|mother[^.\n]*|sibling[^.\n]*|brother[^.\n]*|sister[^.\n]*)'
    matches = re.findall(pattern, transcript)
    if matches:
        return " ".join(set(matches))
    return "None"


def clean_answer(ans, remove_phrases=[]):
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
    bads = ["years old", "none", "nothing", "not mentioned", "no", "n/a", "any"]
    if field != "Age" and ans and any(bad in ans.lower() for bad in bads):
        return True
    if ans and ans.strip().isdigit():
        return True
    if field != "ChiefComplaint" and ans and len(ans) < 3:
        return True
    return False


def extract_patient_info_refined(transcript_text):
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

    # Patient name extraction
    doc = nlp(transcript_text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            info["PatientName"] = ent.text.strip()
            break

    # Gender extraction
    gend_match = re.search(r'\b(male|female|man|woman|boy|girl)\b', transcript_text, re.I)
    if gend_match:
        gender = gend_match.group(1).lower()
        info["Gender"] = {
            "male": "Male", "man": "Male", "boy": "Male",
            "female": "Female", "woman": "Female", "gNirl": "Female"
        }.get(gender, gender.capitalize())

    # Age extraction
    age_patterns = [
        r'(\d{1,3})\s*[-–—]?\s*year(s)?\s*old',
        r'aged\s*(\d{1,3})',
        r'(\d{1,3})\s*y/o',
        r'(\d{1,3})\s*years\s*of\s*age',
        r'(\d{1,3})\s*yo\b',
    ]
    for pattern in age_patterns:
        match = re.search(pattern, transcript_text, re.IGNORECASE)
        if match:
            info['Age'] = next((g for g in match.groups() if g and g.isdigit()), None)
            if info['Age']:
                break

    questions = {
        "ChiefComplaint": ["What is the patient's main complaint?", "Why did the patient come today?"],
        "PastMedicalHistory": ["What is the patient's past medical history?",
                               "Has the patient had any prior illnesses?"],
        "FamilyHistory": ["What is the patient's family history?", "Describe the patient's family illnesses."],
        "PreviousSurgeries": ["Has the patient had any previous surgeries?",
                              "What surgeries has the patient undergone?"],
        "Lifestyle": ["Describe the patient's lifestyle.", "Does the patient smoke or drink?"],
        "Allergies": ["What allergies does the patient have?",
                      "Is the patient allergic to any medication or substance?"],
        "CurrentMedications": ["What medications is the patient currently taking?",
                               "Which drugs does the patient take?"],
    }

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

    for field, qs in questions.items():
        answer_text = None
        for q in qs:
            try:
                result = qa(question=q, context=transcript_text)
                ans = result.get('answer', '').strip()
                ans = clean_answer(ans, removal_phrases.get(field, []))
                if ans and not is_bad_answer(ans, field):
                    answer_text = ans
                    break
            except Exception:
                continue

        if field == "FamilyHistory":
            if not answer_text or answer_text.lower() in ['none', 'no', '']:
                answer_text = improve_family_history_extraction(transcript_text)

        if field == "CurrentMedications" and answer_text:
            meds = extract_medications(answer_text)
            answer_text = ', '.join(meds)

        if not answer_text:
            keywords = [field.replace("History", " history").replace("ChiefComplaint", "complaint").replace(
                "CurrentMedications", "medication").replace("PreviousSurgeries", "surgery").replace(
                "PastMedicalHistory", "illness").lower()]
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

# ---- MAIN ----
if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    transcript_path = os.path.join(BASE_DIR, "transcripts", "full_transcript.txt")

    if not os.path.isfile(transcript_path):
        raise FileNotFoundError(f"Transcript not found at {transcript_path}")

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()

    results = extract_patient_info_refined(transcript)

    # Save results
    output_path = os.path.join(BASE_DIR, "transcripts", "patient_info.json")
    with open(output_path, "w", encoding="utf-8") as out_f:
        import json

        json.dump(results, out_f, indent=2, ensure_ascii=False)

    print(f"[INFO] Patient info saved to {output_path}\n")
    for field, value in results.items():
        print(f"{field}: {value}\n")
