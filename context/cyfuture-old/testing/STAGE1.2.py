import whisper
import spacy
from spacy.pipeline import EntityRuler
from negspacy.negation import Negex
import csv
import json

# ---------------------- LOAD TERM MAPPING ----------------------
with open(r"C:\\Users\\upart\\Desktop\\cyfuture\\testing\\terms\\full_symptom_mapping.json", encoding='utf-8') as f:
    term_mapping = json.load(f)

# ---------------------- TRANSCRIPTION (WHISPER ON GPU) ----------------------
model = whisper.load_model("base", device="cuda")
result = model.transcribe(r"C:\\Users\\upart\\Desktop\\cyfuture\\audio\\Recording.m4a", fp16=True)
full_transcript = result['text']

print("[INFO] Transcript:")
print(full_transcript)
print("--------------------------------------------------\n")

transcript_path = r"C:\\Users\\upart\\Desktop\\cyfuture\\testing\\transcriptoutputs\\full_transcript.txt"
with open(transcript_path, "w", encoding="utf-8") as tf:
    tf.write(full_transcript)
print(f"[INFO] Full transcript saved to: {transcript_path}")

# ---------------------- NLP PIPELINE ----------------------
# Disable default NER (not useful for medical terms)
nlp = spacy.load("en_core_web_sm", disable=["ner"])
nlp.add_pipe("sentencizer")

# Add custom EntityRuler
ruler = nlp.add_pipe("entity_ruler", config={"phrase_matcher_attr": "LOWER"})

patterns = []
with open(r"C:\\Users\\upart\\Desktop\\cyfuture\\testing\\terms\\full_symptom_mapping.csv", newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        term = row["term"].lower().strip()
        label = row["label"]
        tokens = term.split()

        # Pattern for exact LOWER match
        lower_pattern = [{"LOWER": t} for t in tokens]
        patterns.append({"label": label, "pattern": lower_pattern})

        # Pattern for lemma-based match (handles plurals, verb forms, etc.)
        lemma_pattern = [{"LEMMA": t} for t in tokens]
        patterns.append({"label": label, "pattern": lemma_pattern})

ruler.add_patterns(patterns)

# Add NegEx AFTER entity ruler
nlp.add_pipe("negex", last=True)

doc = nlp(full_transcript)

# ---------------------- DEBUGGING ----------------------
print("\n[DEBUG] Matched entities:")
for ent in doc.ents:
    print(f"- {ent.text} | Label: {ent.label_} | Negated: {ent._.negex}")

# ---------------------- 1. Pure Extraction: Latest Mention ----------------------
entity_status = {}
for ent in doc.ents:
    ent_text = ent.text.lower().strip()
    mapped_term = term_mapping.get(ent_text, ent_text)  # fallback to ent text
    status = "NEGATED" if ent._.negex else "AFFIRMED"
    entity_status[mapped_term] = (ent.label_, status)

print("\n=== Pure Extraction (Latest Mention) ===")
pure_extraction_path = r"C:\\Users\\upart\\Desktop\\cyfuture\\testing\\transcriptoutputs\\pure_extraction.txt"
with open(pure_extraction_path, "w", encoding="utf-8") as f:
    for ent_text, (label, status) in entity_status.items():
        if status == "AFFIRMED":  # only keep affirmed
            print(f"{ent_text} ({label}): {status}")
            f.write(f"{ent_text}\n")

# ---------------------- 2. Analytical Review: Sentence Context ----------------------
print("\n=== Analytical Review (Entities per Sentence) ===")
analytical_review_path = r"C:\\Users\\upart\\Desktop\\cyfuture\\testing\\transcriptoutputs\\analytical_review.txt"
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
