import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
import joblib


# =========================
# LOAD DATASET
# =========================

data = pd.read_csv("jobguard_50000_dataset.csv")

data = data.fillna("")


# =========================
# CREATE TEXT
# =========================

data["text"] = (
    data["job_title"].astype(str) + " " +
    data["company"].astype(str) + " " +
    data["description"].astype(str) + " " +
    data["salary"].astype(str) + " " +
    data["experience"].astype(str) + " " +
    data["location"].astype(str) + " " +
    data["contact"].astype(str) + " " +
    data["job_url"].astype(str)
)


# =========================
# INPUT AND OUTPUT
# =========================

X = data["text"]
y = data["is_fake"]


# =========================
# TRAIN TEST SPLIT
# =========================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


# =========================
# TF-IDF
# =========================

vectorizer = TfidfVectorizer(
    lowercase=True,
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.95,
    sublinear_tf=True
)


X_train_vectorized = vectorizer.fit_transform(X_train)

X_test_vectorized = vectorizer.transform(X_test)


# =========================
# MODEL
# =========================

model = LogisticRegression(
    max_iter=2000,
    C=0.5,
    class_weight="balanced"
)


model.fit(
    X_train_vectorized,
    y_train
)


# =========================
# TEST MODEL
# =========================

prediction = model.predict(
    X_test_vectorized
)


accuracy = accuracy_score(
    y_test,
    prediction
)


print(
    "Model Accuracy:",
    round(accuracy * 100, 2),
    "%"
)


print("\nClassification Report:\n")

print(
    classification_report(
        y_test,
        prediction
    )
)


# =========================
# SAVE MODEL
# =========================

joblib.dump(
    model,
    "jobguard_model.pkl"
)

joblib.dump(
    vectorizer,
    "jobguard_vectorizer.pkl"
)


print("\nModel Saved Successfully")

print(
    "jobguard_model.pkl created"
)

print(
    "jobguard_vectorizer.pkl created"
)