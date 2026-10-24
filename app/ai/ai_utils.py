import os
import json
import joblib
import hashlib
import hmac
import base64
import numpy as np
from datetime import datetime, timedelta
from config import Config
from app.models.models import Complaint
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics.pairwise import cosine_similarity
from flask import current_app
from app.policies import get_target_hours, calculate_deadline

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'models')
VECTORIZER_PATH = os.path.join(MODEL_DIR, 'vectorizer.joblib')
CATEGORY_MODEL_PATH = os.path.join(MODEL_DIR, 'category_model.joblib')
PRIORITY_MODEL_PATH = os.path.join(MODEL_DIR, 'priority_model.joblib')
DURATION_MODEL_PATH = os.path.join(MODEL_DIR, 'duration_model.joblib')
METADATA_PATH = os.path.join(MODEL_DIR, 'model_metadata.json')

_vectorizer = None
_category_model = None
_priority_model = None
_duration_model = None
_metadata = None


# Typical resolution days by category and priority (used as fallback/training data)
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


def load_models():
    global _vectorizer, _category_model, _priority_model, _duration_model, _metadata
    try:
        _vectorizer = joblib.load(VECTORIZER_PATH)
        _category_model = joblib.load(CATEGORY_MODEL_PATH)
        _priority_model = joblib.load(PRIORITY_MODEL_PATH)
        if os.path.exists(DURATION_MODEL_PATH):
            _duration_model = joblib.load(DURATION_MODEL_PATH)
        with open(METADATA_PATH, 'r') as f:
            _metadata = json.load(f)
        return True
    except Exception as e:
        print(f"Failed to load models: {e}")
        return False


def predict_duration(text):
    """Predict resolution duration in days based on complaint text."""
    if _duration_model and _vectorizer:
        try:
            X = _vectorizer.transform([text])
            duration = _duration_model.predict(X)[0]
            return max(1, min(30, round(duration)))
        except Exception:
            pass
    return 5


def get_ai_suggestions(title, description, student_id=None):
    if not _vectorizer or not _category_model or not _priority_model:
        if not load_models():
            return {
                'category': 'Needs manual review',
                'category_confidence': 0,
                'priority': 'Medium',
                'priority_confidence': 0,
                'department': 'Administration',
                'estimated_duration_days': 5,
                'estimated_duration_hours': 120,
                'explanation': 'AI model not available. Please select manually.',
                'similar_complaints': [],
                'needs_manual_review': True,
                'verification_token': None,
                'verification_expires': None
            }
    
    text = f"{title} {description}".strip()
    if len(text) < 25:
        return {
            'category': 'Needs manual review',
            'category_confidence': 0,
            'priority': 'Medium',
            'priority_confidence': 0,
            'department': 'Administration',
            'estimated_duration_days': 5,
            'estimated_duration_hours': 120,
            'explanation': 'Please provide at least 25 characters for AI suggestions.',
            'similar_complaints': [],
            'needs_manual_review': True,
            'verification_token': None,
            'verification_expires': None
        }
    
    X = _vectorizer.transform([text])
    
    cat_proba = _category_model.predict_proba(X)[0]
    cat_idx = np.argmax(cat_proba)
    predicted_category = _category_model.classes_[cat_idx]
    category_confidence = float(cat_proba[cat_idx])
    
    pri_proba = _priority_model.predict_proba(X)[0]
    pri_idx = np.argmax(pri_proba)
    predicted_priority = _priority_model.classes_[pri_idx]
    priority_confidence = float(pri_proba[pri_idx])
    
    suggested_department = Config.CATEGORY_DEPARTMENT_MAP.get(predicted_category, 'Administration')
    
    needs_manual_review = category_confidence < Config.AI_CONFIDENCE_THRESHOLD or priority_confidence < Config.AI_CONFIDENCE_THRESHOLD
    
    estimated_duration = predict_duration(text)
    estimated_hours = get_target_hours(predicted_priority)
    
    feature_names = _vectorizer.get_feature_names_out()
    text_vector = X.toarray()[0]
    top_indices = text_vector.argsort()[-5:][::-1]
    top_keywords = [feature_names[i] for i in top_indices if text_vector[i] > 0]
    explanation = f"Key terms: {', '.join(top_keywords)}" if top_keywords else "No strong keywords detected."
    
    similar_complaints = find_similar_complaints(text, top_n=3)
    
    # Generate verification token
    verification_token, expires_at = _generate_verification_token(
        title, description, predicted_category, predicted_priority, estimated_duration
    )
    
    return {
        'category': predicted_category,
        'category_confidence': round(category_confidence * 100, 1),
        'priority': predicted_priority,
        'priority_confidence': round(priority_confidence * 100, 1),
        'department': suggested_department,
        'estimated_duration_days': estimated_duration,
        'estimated_duration_hours': estimated_hours,
        'explanation': explanation,
        'similar_complaints': similar_complaints,
        'needs_manual_review': needs_manual_review,
        'verification_token': verification_token,
        'verification_expires': expires_at.isoformat() if expires_at else None
    }


def find_similar_complaints(text, top_n=3):
    complaints = Complaint.query.filter(
        Complaint.category.isnot(None),
        Complaint.description.isnot(None)
    ).limit(200).all()
    
    if not complaints:
        return []
    
    corpus = [f"{c.title} {c.description}" for c in complaints]
    corpus_vec = _vectorizer.transform(corpus)
    query_vec = _vectorizer.transform([text])
    
    similarities = cosine_similarity(query_vec, corpus_vec).flatten()
    top_indices = similarities.argsort()[-top_n:][::-1]
    
    results = []
    for idx in top_indices:
        if similarities[idx] > 0.1:
            c = complaints[idx]
            results.append({
                'ticket_number': c.ticket_number,
                'title': c.title[:80],
                'category': c.category,
                'similarity': round(float(similarities[idx]) * 100, 1)
            })
    
    return results


def _generate_verification_token(title, description, category, priority, duration):
    """Generate a signed verification token bound to complaint text and prediction."""
    try:
        # Create payload
        payload = {
            'title': title.strip(),
            'description': description.strip(),
            'category': category,
            'priority': priority,
            'duration': duration,
            'timestamp': datetime.utcnow().isoformat(),
            'expires': (datetime.utcnow() + timedelta(minutes=30)).isoformat()
        }
        
        # Serialize payload
        import json
        payload_json = json.dumps(payload, sort_keys=True).encode('utf-8')
        
        # Generate signature using Flask's secret key
        if current_app:
            secret = current_app.config.get('SECRET_KEY', Config.SECRET_KEY)
        else:
            secret = Config.SECRET_KEY
        
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_json,
            hashlib.sha256
        ).digest()
        
        # Combine payload and signature
        token_data = base64.urlsafe_b64encode(payload_json).decode('utf-8')
        sig_b64 = base64.urlsafe_b64encode(signature).decode('utf-8')
        token = f"{token_data}.{sig_b64}"
        
        expires_at = datetime.utcnow() + timedelta(minutes=30)
        return token, expires_at
    except Exception as e:
        print(f"Failed to generate verification token: {e}")
        return None, None


def verify_verification_token(token, title, description, student_id=None):
    """Verify a verification token and return the payload if valid."""
    try:
        if not token or '.' not in token:
            return {'valid': False, 'error': 'Invalid token format'}
        
        token_data, sig_b64 = token.rsplit('.', 1)
        
        # Decode payload
        payload_json = base64.urlsafe_b64decode(token_data + '==')
        payload = json.loads(payload_json.decode('utf-8'))
        
        # Verify signature
        if current_app:
            secret = current_app.config.get('SECRET_KEY', Config.SECRET_KEY)
        else:
            secret = Config.SECRET_KEY
        
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload_json,
            hashlib.sha256
        ).digest()
        
        provided_signature = base64.urlsafe_b64decode(sig_b64 + '==')
        
        if not hmac.compare_digest(expected_signature, provided_signature):
            return {'valid': False, 'error': 'Invalid signature'}
        
        # Check expiration
        expires_at = datetime.fromisoformat(payload['expires'])
        if datetime.utcnow() > expires_at:
            return {'valid': False, 'error': 'Verification token expired'}
        
        # Verify text matches
        if payload['title'].strip() != title.strip() or payload['description'].strip() != description.strip():
            return {'valid': False, 'error': 'Complaint text changed after verification'}
        
        # Verify student if provided
        if student_id is not None:
            # Could add student_id to payload in future
            pass
        
        return {
            'valid': True,
            'category': payload['category'],
            'priority': payload['priority'],
            'duration': payload['duration'],
            'expires': payload['expires']
        }
    except Exception as e:
        return {'valid': False, 'error': f'Verification failed: {str(e)}'}


def find_similar_complaints(text, top_n=3):
    """Find similar complaints using cosine similarity."""
    if not _vectorizer or not _category_model or not _priority_model:
        if not load_models():
            return []
    
    complaints = Complaint.query.filter(
        Complaint.category.isnot(None),
        Complaint.description.isnot(None)
    ).limit(200).all()
    
    if not complaints:
        return []
    
    corpus = [f"{c.title} {c.description}" for c in complaints]
    corpus_vec = _vectorizer.transform(corpus)
    query_vec = _vectorizer.transform([text])
    
    similarities = cosine_similarity(query_vec, corpus_vec).flatten()
    top_indices = similarities.argsort()[-top_n:][::-1]
    
    results = []
    for idx in top_indices:
        if similarities[idx] > 0.1:
            c = complaints[idx]
            results.append({
                'ticket_number': c.ticket_number,
                'title': c.title[:80],
                'category': c.category,
                'similarity': round(float(similarities[idx]) * 100, 1)
            })
    
    return results


def find_duplicates(complaint, threshold=0.7):
    """Find potential duplicate complaints."""
    if not _vectorizer:
        if not load_models():
            return []
    
    existing = Complaint.query.filter(
        Complaint.id != complaint.id,
        Complaint.category.isnot(None),
        Complaint.description.isnot(None)
    ).limit(200).all()
    
    if not existing:
        return []
    
    corpus = [f"{c.title} {c.description}" for c in existing]
    corpus_vec = _vectorizer.transform(corpus)
    query_vec = _vectorizer.transform([f"{complaint.title} {complaint.description}"])
    
    similarities = cosine_similarity(query_vec, corpus_vec).flatten()
    results = []
    
    for idx in similarities.argsort()[::-1]:
        if similarities[idx] >= threshold:
            c = existing[idx]
            results.append({
                'ticket_number': c.ticket_number,
                'title': c.title,
                'category': c.category,
                'status': c.status,
                'similarity': round(float(similarities[idx]) * 100, 1),
            })
    
    return results


def train_models():
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score, confusion_matrix, mean_absolute_error
    
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'sample_complaints.csv')
    df = pd.read_csv(csv_path)
    
    df['text'] = df['title'].fillna('') + ' ' + df['description'].fillna('')
    df = df.dropna(subset=['text', 'category', 'priority'])
    
    vectorizer = TfidfVectorizer(stop_words='english', max_features=5000, ngram_range=(1, 2))
    X = vectorizer.fit_transform(df['text'])
    
    y_cat = df['category']
    y_pri = df['priority']
    y_dur = df['resolution_time_days'] if 'resolution_time_days' in df.columns else df.apply(
        lambda r: CATEGORY_PRIORITY_DURATION.get(r['category'], {}).get(r['priority'], 5), axis=1
    )
    
    cat_model = LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')
    pri_model = LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')
    dur_model = RandomForestRegressor(n_estimators=100, random_state=42)
    
    cat_model.fit(X, y_cat)
    pri_model.fit(X, y_pri)
    dur_model.fit(X, y_dur)
    
    cat_pred = cat_model.predict(X)
    pri_pred = pri_model.predict(X)
    dur_pred = dur_model.predict(X)
    
    cat_accuracy = accuracy_score(y_cat, cat_pred)
    pri_accuracy = accuracy_score(y_pri, pri_pred)
    dur_mae = mean_absolute_error(y_dur, dur_pred)
    
    cat_report = classification_report(y_cat, cat_pred, output_dict=True, zero_division=0)
    pri_report = classification_report(y_pri, pri_pred, output_dict=True, zero_division=0)
    
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    joblib.dump(cat_model, CATEGORY_MODEL_PATH)
    joblib.dump(pri_model, PRIORITY_MODEL_PATH)
    joblib.dump(dur_model, DURATION_MODEL_PATH)
    
    metadata = {
        'algorithm': 'LogisticRegression with TF-IDF (category/priority), RandomForestRegressor with TF-IDF (duration)',
        'training_date': datetime.utcnow().isoformat(),
        'dataset_records': len(df),
        'categories': list(df['category'].unique()),
        'priorities': list(df['priority'].unique()),
        'category_accuracy': round(cat_accuracy, 4),
        'priority_accuracy': round(pri_accuracy, 4),
        'duration_mae': round(dur_mae, 4),
        'category_report': cat_report,
        'priority_report': pri_report
    }
    
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return metadata