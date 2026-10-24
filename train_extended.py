import os
import sys
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score, mean_absolute_error, confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
VECTORIZER_PATH = os.path.join(MODEL_DIR, 'vectorizer.joblib')
CATEGORY_MODEL_PATH = os.path.join(MODEL_DIR, 'category_model.joblib')
PRIORITY_MODEL_PATH = os.path.join(MODEL_DIR, 'priority_model.joblib')
DURATION_MODEL_PATH = os.path.join(MODEL_DIR, 'duration_model.joblib')
METADATA_PATH = os.path.join(MODEL_DIR, 'model_metadata.json')

CATEGORY_PRIORITY_DURATION = {
    'Hostel': {'Critical': 1, 'High': 2, 'Medium': 4, 'Low': 7},
    'IT Support': {'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 5},
    'Library': {'Critical': 1, 'High': 3, 'Medium': 5, 'Low': 7},
    'Transport': {'Critical': 1, 'High': 2, 'Medium': 4, 'Low': 7},
    'Examination': {'Critical': 1, 'High': 3, 'Medium': 5, 'Low': 7},
    'Fees and Accounts': {'Critical': 1, 'High': 2, 'Medium': 4, 'Low': 7},
    'Campus Facilities': {'Critical': 1, 'High': 2, 'Medium': 4, 'Low': 7},
    'Placement': {'Critical': 2, 'High': 3, 'Medium': 5, 'Low': 7},
    'Academics': {'Critical': 2, 'High': 4, 'Medium': 7, 'Low': 10},
    'Student Wellbeing': {'Critical': 1, 'High': 2, 'Medium': 4, 'Low': 7},
    'Other': {'Critical': 2, 'High': 3, 'Medium': 5, 'Low': 7},
}


def load_data():
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'extended_complaints.csv')
    if not os.path.exists(csv_path):
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sample_complaints.csv')
    
    df = pd.read_csv(csv_path)
    df['text'] = df['title'].fillna('') + ' ' + df['description'].fillna('')
    df = df.dropna(subset=['text', 'category', 'priority'])
    
    print(f"Loaded {len(df)} records from {csv_path}")
    return df


def train_models():
    df = load_data()
    
    vectorizer = TfidfVectorizer(
        stop_words='english', 
        max_features=5000, 
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95
    )
    X = vectorizer.fit_transform(df['text'])
    
    y_cat = df['category']
    y_pri = df['priority']
    y_dur = df['resolution_time_days'] if 'resolution_time_days' in df.columns else df.apply(
        lambda r: CATEGORY_PRIORITY_DURATION.get(r['category'], {}).get(r['priority'], 5), axis=1
    )
    
    print(f"Categories: {sorted(y_cat.unique())}")
    print(f"Priorities: {sorted(y_pri.unique())}")
    print(f"Duration range: {y_dur.min()} - {y_dur.max()} days")
    
    X_train, X_test, y_cat_train, y_cat_test, y_pri_train, y_pri_test, y_dur_train, y_dur_test = train_test_split(
        X, y_cat, y_pri, y_dur, test_size=0.2, random_state=42, stratify=y_cat
    )
    
    print("\nTraining Category Model (LogisticRegression)...")
    cat_model = LogisticRegression(max_iter=2000, random_state=42, class_weight='balanced', C=1.0, solver='lbfgs')
    cat_model.fit(X_train, y_cat_train)
    
    cat_pred = cat_model.predict(X_test)
    cat_accuracy = accuracy_score(y_cat_test, cat_pred)
    cat_report = classification_report(y_cat_test, cat_pred, output_dict=True, zero_division=0)
    print(f"Category Accuracy: {cat_accuracy:.4f}")
    print(classification_report(y_cat_test, cat_pred, zero_division=0))
    
    print("\nTraining Priority Model (LogisticRegression)...")
    pri_model = LogisticRegression(max_iter=2000, random_state=42, class_weight='balanced', C=1.0, solver='lbfgs')
    pri_model.fit(X_train, y_pri_train)
    
    pri_pred = pri_model.predict(X_test)
    pri_accuracy = accuracy_score(y_pri_test, pri_pred)
    pri_report = classification_report(y_pri_test, pri_pred, output_dict=True, zero_division=0)
    print(f"Priority Accuracy: {pri_accuracy:.4f}")
    print(classification_report(y_pri_test, pri_pred, zero_division=0))
    
    print("\nTraining Duration Model (RandomForestRegressor)...")
    dur_model = RandomForestRegressor(n_estimators=200, random_state=42, max_depth=15, min_samples_split=5, n_jobs=-1)
    dur_model.fit(X_train, y_dur_train)
    
    dur_pred = dur_model.predict(X_test)
    dur_mae = mean_absolute_error(y_dur_test, dur_pred)
    print(f"Duration MAE: {dur_mae:.4f} days")
    print(f"Duration predictions: min={dur_pred.min():.1f}, max={dur_pred.max():.1f}, mean={dur_pred.mean():.1f}")
    print(f"Actual duration: min={y_dur_test.min()}, max={y_dur_test.max()}, mean={y_dur_test.mean():.1f}")
    
    cv_cat = cross_val_score(cat_model, X, y_cat, cv=5, scoring='accuracy', n_jobs=-1)
    cv_pri = cross_val_score(pri_model, X, y_pri, cv=5, scoring='accuracy', n_jobs=-1)
    cv_dur = cross_val_score(dur_model, X, y_dur, cv=5, scoring='neg_mean_absolute_error', n_jobs=-1)
    print(f"\nCross-validation:")
    print(f"  Category CV Accuracy: {cv_cat.mean():.4f} (+/- {cv_cat.std()*2:.4f})")
    print(f"  Priority CV Accuracy: {cv_pri.mean():.4f} (+/- {cv_pri.std()*2:.4f})")
    print(f"  Duration CV MAE: {-cv_dur.mean():.4f} (+/- {cv_dur.std()*2:.4f})")
    
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    joblib.dump(cat_model, CATEGORY_MODEL_PATH)
    joblib.dump(pri_model, PRIORITY_MODEL_PATH)
    joblib.dump(dur_model, DURATION_MODEL_PATH)
    print(f"\nModels saved to {MODEL_DIR}")
    
    metadata = {
        'algorithm': 'LogisticRegression with TF-IDF (category/priority), RandomForestRegressor with TF-IDF (duration)',
        'training_date': datetime.utcnow().isoformat(),
        'dataset_records': len(df),
        'categories': sorted(df['category'].unique().tolist()),
        'priorities': sorted(df['priority'].unique().tolist()),
        'category_accuracy': round(cat_accuracy, 4),
        'priority_accuracy': round(pri_accuracy, 4),
        'duration_mae': round(dur_mae, 4),
        'category_cv_accuracy': round(cv_cat.mean(), 4),
        'priority_cv_accuracy': round(cv_pri.mean(), 4),
        'duration_cv_mae': round(-cv_dur.mean(), 4),
        'category_report': cat_report,
        'priority_report': pri_report,
    }
    
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nMetadata saved to {METADATA_PATH}")
    
    return metadata


if __name__ == '__main__':
    print("Training AI models with extended dataset...")
    metadata = train_models()
    print(f"\nTraining complete!")
    print(f"Dataset records: {metadata['dataset_records']}")
    print(f"Category accuracy: {metadata['category_accuracy']:.4f}")
    print(f"Priority accuracy: {metadata['priority_accuracy']:.4f}")
    print(f"Duration MAE: {metadata['duration_mae']:.4f}")
    print(f"Categories: {metadata['categories']}")
    print(f"Priorities: {metadata['priorities']}")