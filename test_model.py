import joblib
import numpy as np

# Load models
vectorizer = joblib.load('models/vectorizer.joblib')
category_model = joblib.load('models/category_model.joblib')
priority_model = joblib.load('models/priority_model.joblib')

# Test with training data
text = 'Water supply issue in hostel No water in hostel block A since morning. Students cannot bathe or use washrooms. Urgent attention needed.'
X = vectorizer.transform([text])

cat_proba = category_model.predict_proba(X)[0]
cat_idx = np.argmax(cat_proba)
predicted_category = category_model.classes_[cat_idx]
category_confidence = float(cat_proba[cat_idx])

pri_proba = priority_model.predict_proba(X)[0]
pri_idx = np.argmax(pri_proba)
predicted_priority = priority_model.classes_[pri_idx]
priority_confidence = float(pri_proba[pri_idx])

print('Text:', text)
print('Category:', predicted_category, category_confidence)
print('Priority:', predicted_priority, priority_confidence)
print()
print('Category classes:', category_model.classes_)
print('Category probs:', cat_proba)
print()
print('Priority classes:', priority_model.classes_)
print('Priority probs:', pri_proba)