import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import os

# Load datasets
df = pd.read_csv("./transformed_symptoms_dataset_full (1).csv")
TriagePriority = pd.read_csv("./filtered_disease_triage_priority.csv")

# Prepare features and target
X_noisy = df.drop(["Disease"], axis=1)
y = df["Disease"]

# Split data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X_noisy, y, test_size=0.1, random_state=42)

# Train Random Forest model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Make sure ml_model directory exists
save_dir = r"C:\Users\upart\Desktop\medicalpipeline\ml_model"
os.makedirs(save_dir, exist_ok=True)

# Save the trained model
model_path = os.path.join(save_dir, "model.pkl")
joblib.dump(model, model_path)
print(f"[INFO] Model saved to {model_path}")

# Prediction function
def predict_top5(symptoms, model, df, X):
    new_entry = dict.fromkeys(df.columns, 0)
    new_entry["Disease"] = None
    for s in symptoms:
        if s in new_entry:
            new_entry[s] = 1

    input_df = pd.DataFrame([new_entry])[X.columns]

    probas = model.predict_proba(input_df)[0]
    disease_probas = dict(zip(model.classes_, probas))

    top5 = sorted(disease_probas.items(), key=lambda x: x[1], reverse=True)[:5]
    return top5

# Example use: Read symptoms from file and predict top diseases
with open("C:/Users/upart/Desktop/cyfuture/testing/transcriptoutputs/pure_extraction.txt") as abc:
    symptom_list = abc.read().splitlines()

top5_predictions = predict_top5(symptom_list, model, df, X_noisy)

count=0
for disease, score in top5_predictions:
    if score > 0.33:
        count += 1
        temp = TriagePriority[TriagePriority["Disease"] == disease]
        priority_score = temp['Priority Score'].values[0]
        print(f"{disease}: {score:.4f} | Priority: {priority_score}")

if count == 0:
    print("Can't predict with accuracy")
