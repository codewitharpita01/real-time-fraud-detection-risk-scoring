import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scamguard.rule_engine import detect_indicators, has_strong_evidence, rule_score
from src.scamguard.text import normalize_batch, normalize_text

LABELS = ["scam", "legitimate", "ambiguous"]
RISK_LABELS = ["Low Risk", "Medium Risk", "High Risk", "Needs Manual Review"]
REQUIRED = {"text", "label", "category", "language", "source_type", "source_id"}


def load_split(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path)
    missing = REQUIRED - set(data.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")
    data = data.dropna(subset=list(REQUIRED))
    for column in REQUIRED:
        data[column] = data[column].astype(str).str.strip()
    data["label"] = data["label"].str.lower()
    data = data[data.text.ne("")].copy()
    unexpected = set(data.label) - set(LABELS)
    if unexpected:
        raise ValueError(f"{path} contains unsupported labels: {', '.join(sorted(unexpected))}")
    data["normalized_text"] = data.text.map(normalize_text)
    return data


def build_pipeline() -> Pipeline:
    word_and_char = FeatureUnion([
        ("word_tfidf", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1, max_features=80_000, sublinear_tf=True)),
        ("char_tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, max_features=120_000, sublinear_tf=True)),
    ])
    return Pipeline([
        ("normalize", FunctionTransformer(normalize_batch, validate=False)),
        ("features", word_and_char),
        ("classifier", LogisticRegression(class_weight="balanced", max_iter=2000, C=2.0, random_state=42)),
    ])


def get_model_outputs(model, records):
    probabilities = model.predict_proba(records.text.tolist())
    class_to_col = {str(label): index for index, label in enumerate(model.classes_)}
    return [
        {str(label): float(row[class_to_col[str(label)]]) for label in model.classes_}
        for row in probabilities
    ]


def combine_score(probabilities, text):
    indicators = detect_indicators(text)
    rules = rule_score(indicators)
    scam_probability = probabilities.get("scam", 0.0)
    score = round(0.60 * rules + 0.40 * scam_probability * 100)
    strong = has_strong_evidence(indicators)
    return min(100, max(60 if strong else 0, score)), strong


def classify_risk(score, probabilities, low_max, high_min, ambiguity_cutoff=0.40, strong=False):
    if strong or score >= high_min:
        return "High Risk"
    if probabilities.get("ambiguous", 0.0) >= ambiguity_cutoff:
        return "Needs Manual Review"
    if score > low_max:
        return "Medium Risk"
    return "Low Risk"


def tune_risk_thresholds(model, validation):
    outputs = get_model_outputs(model, validation)
    labels = validation.label.tolist()
    scores = [combine_score(output, text)[0] for output, text in zip(outputs, validation.text)]
    truths = ["High Risk" if label == "scam" else "Low Risk" if label == "legitimate" else "Needs Manual Review" for label in labels]
    best = None
    for low_max in range(25, 31, 2):
        for high_min in range(55, 66, 5):
            if high_min <= low_max + 15:
                continue
            predictions = [
                classify_risk(score, output, low_max, high_min, strong=has_strong_evidence(detect_indicators(text)))
                for score, output, text in zip(scores, outputs, validation.text)
            ]
            macro = f1_score(truths, predictions, labels=RISK_LABELS, average="macro", zero_division=0)
            candidate = (macro, low_max, high_min)
            if best is None or candidate[0] > best[0]:
                best = candidate
    return {"low_max": best[1], "high_min": best[2], "manual_ambiguity_probability": 0.40,
            "validation_macro_f1": round(best[0], 4), "tuned_on": "validation split only"}


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate the local hybrid text model from fixed disjoint splits.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    splits = {name: load_split(args.data_dir / f"{name}.csv") for name in ("train", "validation", "test")}
    for name, data in splits.items():
        missing_labels = set(LABELS) - set(data.label.unique())
        if missing_labels:
            raise SystemExit(f"{name} split is missing labels: {', '.join(sorted(missing_labels))}")
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        a, b = splits[left], splits[right]
        duplicates = set(a.normalized_text) & set(b.normalized_text)
        groups = set(a.source_id) & set(b.source_id)
        if duplicates or groups:
            raise SystemExit(f"Leakage check failed between {left} and {right}: {len(duplicates)} duplicate texts, {len(groups)} shared source IDs.")

    train, validation, test = splits["train"], splits["validation"], splits["test"]
    model = build_pipeline()
    model.fit(train.text.tolist(), train.label.tolist())
    thresholds = tune_risk_thresholds(model, validation)
    test_outputs = get_model_outputs(model, test)
    predicted_labels = [max(item, key=item.get) for item in test_outputs]
    predictions = [combine_score(item, text) for item, text in zip(test_outputs, test.text)]
    scores = [item[0] for item in predictions]
    strong_flags = [item[1] for item in predictions]
    predicted_risk = [classify_risk(score, output, thresholds["low_max"], thresholds["high_min"],
                                    thresholds["manual_ambiguity_probability"], strong)
                      for score, output, strong in zip(scores, test_outputs, strong_flags)]
    true_risk = ["High Risk" if label == "scam" else "Low Risk" if label == "legitimate" else "Needs Manual Review" for label in test.label]

    report_by_language = {}
    for language, group in test.groupby("language"):
        index = group.index.tolist()
        local_predictions = [predicted_labels[position] for position in index]
        report_by_language[language] = classification_report(group.label, local_predictions, labels=LABELS, output_dict=True, zero_division=0)
    report_by_category = {}
    for category, group in test.groupby("category"):
        index = group.index.tolist()
        local_predictions = [predicted_labels[position] for position in index]
        report_by_category[category] = classification_report(group.label, local_predictions, labels=LABELS, output_dict=True, zero_division=0)

    false_positives, false_negatives = [], []
    model_false_positives, model_false_negatives = [], []
    for index, row in test.reset_index(drop=True).iterrows():
        record = {"category": row.category, "language": row.language, "text": row.text,
                  "actual": row.label, "predicted": predicted_labels[index], "risk_level": predicted_risk[index]}
        if row.label != "scam" and predicted_risk[index] == "High Risk":
            false_positives.append(record)
        if row.label == "scam" and predicted_risk[index] != "High Risk":
            false_negatives.append(record)
        if row.label != "scam" and predicted_labels[index] == "scam":
            model_false_positives.append(record)
        if row.label == "scam" and predicted_labels[index] != "scam":
            model_false_negatives.append(record)

    args.output.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, args.output / "text_model.joblib")
    joblib.dump(model.named_steps["features"], args.output / "tfidf_vectorizer.joblib")
    (args.output / "risk_thresholds.json").write_text(json.dumps(thresholds, indent=2), encoding="utf-8")
    metadata = {
        "dataset_status": "synthetic educational seed data; not real confirmed scam reports",
        "split_sizes": {name: int(len(data)) for name, data in splits.items()},
        "split_label_counts": {name: {str(k): int(v) for k, v in data.label.value_counts().items()} for name, data in splits.items()},
        "source_types": sorted(set().union(*(set(data.source_type) for data in splits.values()))),
        "model": "word TF-IDF (1-2 grams) + character TF-IDF (3-5 grams) + class-weighted Logistic Regression",
        "normalization": "Unicode NFKC, casefold, zero-width removal, whitespace collapse; same function for train/inference",
        "validation_tuned_risk_thresholds": thresholds,
        "test_text_classification_report": classification_report(test.label, predicted_labels, labels=LABELS, output_dict=True, zero_division=0),
        "test_confusion_matrix_labels_scam_legitimate_ambiguous": confusion_matrix(test.label, predicted_labels, labels=LABELS).tolist(),
        "test_risk_classification_report": classification_report(true_risk, predicted_risk, labels=RISK_LABELS, output_dict=True, zero_division=0),
        "test_risk_confusion_matrix_labels_low_medium_high_manual": confusion_matrix(true_risk, predicted_risk, labels=RISK_LABELS).tolist(),
        "per_language_test_report": report_by_language,
        "per_category_test_report": report_by_category,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "model_false_positives": model_false_positives,
        "model_false_negatives": model_false_negatives,
        "false_positive_negative_summary": {
            "text_model_false_positives": len(model_false_positives),
            "text_model_false_negatives": len(model_false_negatives),
            "hybrid_high_risk_false_positives": len(false_positives),
            "hybrid_high_risk_false_negatives": len(false_negatives),
            "definition": "Model FP/FN use scam as positive class; hybrid FP/FN use High Risk against scam labels. All records are synthetic.",
        },
        "limitations": "All bundled records are synthetic. These metrics measure only this authored benchmark and do not estimate performance on real or future fraud. Obtain independent, legally usable, source-documented real data before making deployment claims.",
    }
    (args.output / "metrics.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(metadata, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
