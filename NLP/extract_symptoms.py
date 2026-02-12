import spacy
from spacy.pipeline import EntityRuler
from negspacy.negation import Negex
import csv
import json
import os

# ---------------- PATH SETUP ----------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Input files
transcript_path    = os.path.join(BASE_DIR, "transcripts", "full_transcript.txt")
mapping_json_path  = os.path.join(BASE_DIR, "terms", "full_symptom_mapping.json")
mapping_csv_path   = os.path.join(BASE_DIR, "terms", "full_symptom_mapping.csv")

# Output directory
output_dir = os.path.join(BASE_DIR, "transcripts")
os.makedirs(output_dir, exist_ok=True)

# ---------------- LOAD TERM MAPPING ----------------
with open(mapping_json_path, encoding='utf-8') as f:
    term_mapping = json.load(f)

# ---------------- LOAD TRANSCRIPT ----------------
with open(transcript_path, "r", encoding="utf-8") as tf:
    full_transcript = tf.read()

# ---------------- NLP PIPELINE ----------------
nlp = spacy.load("en_core_web_sm", disable=["ner"])
nlp.add_pipe("sentencizer")

ruler = nlp.add_pipe("entity_ruler", config={"phrase_matcher_attr": "LOWER"})

patterns = []
with open(mapping_csv_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        term = row["term"].lower().strip()
        label = row["label"]
        tokens = term.split()

        lower_pattern = [{"LOWER": t} for t in tokens]
        lemma_pattern = [{"LEMMA": t} for t in tokens]

        patterns.append({"label": label, "pattern": lower_pattern})
        patterns.append({"label": label, "pattern": lemma_pattern})

ruler.add_patterns(patterns)

# Add NegEx
nlp.add_pipe("negex", last=True)
doc = nlp(full_transcript)

# ---------------- PURE EXTRACTION ----------------
entity_status = {}
for ent in doc.ents:
    ent_text = ent.text.lower().strip()
    mapped_term = term_mapping.get(ent_text, ent_text)  # fallback if not in mapping
    status = "NEGATED" if ent._.negex else "AFFIRMED"
    entity_status[mapped_term] = (ent.label_, status)

pure_extraction_path = os.path.join(output_dir, "pure_extraction.txt")
with open(pure_extraction_path, "w", encoding="utf-8") as f:
    for ent_text, (label, status) in entity_status.items():
        if status == "AFFIRMED":
            print(f"{ent_text} ({label}): {status}")
            f.write(f"{ent_text}\n")

# ---------------- ANALYTICAL REVIEW ----------------
analytical_review_path = os.path.join(output_dir, "analytical_review.txt")
with open(analytical_review_path, "w", encoding="utf-8") as f:
    for sent in doc.sents:
        entities_in_sent = []
        for ent in sent.ents:
            ent_text = ent.text.lower().strip()
            mapped_term = term_mapping.get(ent_text, ent_text)
            status = "NEGATED" if ent._.negex else "AFFIRMED"
            entities_in_sent.append((mapped_term, ent.label_, status))
        if entities_in_sent:
            print(f"\nSentence: {sent.text.strip()}")
            f.write(f"{sent.text.strip()}\n")
            for ent_text, label, status in entities_in_sent:
                print(f"  - {ent_text} ({label}): {status}")
            f.write("\n")

print(f"\n[INFO] Pure extraction saved to: {pure_extraction_path}")
print(f"[INFO] Analytical review saved to: {analytical_review_path}")
