import whisper
import spacy
from spacy.pipeline import EntityRuler
import negspacy
from negspacy.negation import Negex
import csv
import json

# Load your complete term mapping dictionary
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

# ---------------------- NLP + ENTITYRULER + NEGEX ----------------------
nlp = spacy.load("en_core_web_sm")
nlp.add_pipe("sentencizer")
ruler = nlp.add_pipe("entity_ruler", before="ner", config={"phrase_matcher_attr": "LOWER"})

patterns = []
with open(r"C:\\Users\\upart\\Desktop\\cyfuture\\testing\\terms\\symptoms.csv", newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        patterns.append({"label": row["label"], "pattern": row["term"]})
ruler.add_patterns(patterns)
nlp.add_pipe("negex", last=True)

doc = nlp(full_transcript)

# ---------------------- 1. Pure Extraction: Latest Mention with Mapping ----------------------
entity_status = {}
for ent in doc.ents:
    mapped_term = term_mapping.get(ent.text.lower())
    if mapped_term:
        status = "NEGATED" if ent._.negex else "AFFIRMED"
        entity_status[mapped_term] = (ent.label_, status)

print("\n=== Pure Extraction (Latest Mention) ===")

pure_extraction_path = r"C:\\Users\\upart\\Desktop\\cyfuture\\testing\\transcriptoutputs\\pure_extraction.txt"
with open(pure_extraction_path, "w", encoding="utf-8") as f:
    for ent_text, (label, status) in entity_status.items():
        if status == "AFFIRMED":
            print(f"{ent_text} ({label}): {status}")
            f.write(f"{ent_text}\n")

# ---------------------- 2. Analytical Review: Sentence Context with Mapping ----------------------
print("\n=== Analytical Review (Entities per Sentence) ===")
analytical_review_path = r"C:\\Users\\upart\\Desktop\\cyfuture\\testing\\transcriptoutputs\\analytical_review.txt"
with open(analytical_review_path, "w", encoding="utf-8") as f:
    for sent in doc.sents:
        entities_in_sent = []
        for ent in sent.ents:
            mapped_term = term_mapping.get(ent.text.lower())
            if mapped_term:
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
