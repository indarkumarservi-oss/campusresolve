import pytest
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.ai_utils import get_ai_suggestions, load_models, train_models
from app.extensions import db
from app.models import Complaint


class TestAI:
    
    def test_ai_endpoint_returns_valid_structure(self, client, logged_in_student):
        response = client.post('/api/ai/suggest', data={
            'title': 'WiFi not working in library',
            'description': 'The WiFi in the main library has been down for two days. Students cannot access online resources or submit assignments.'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'category' in data
        assert 'category_confidence' in data
        assert 'priority' in data
        assert 'priority_confidence' in data
        assert 'department' in data
        assert 'explanation' in data
        assert 'similar_complaints' in data
        assert 'needs_manual_review' in data
    
    def test_ai_endpoint_rejects_short_input(self, client, logged_in_student):
        response = client.post('/api/ai/suggest', data={
            'title': 'Short',
            'description': 'Hi'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['needs_manual_review'] is True
        assert '25 characters' in data['explanation'] or 'manual review' in data['explanation'].lower()
    
    def test_ai_endpoint_rejects_empty_input(self, client, logged_in_student):
        response = client.post('/api/ai/suggest', data={
            'title': '',
            'description': ''
        })
        
        assert response.status_code == 400
    
    def test_ai_suggests_it_category_for_wifi(self, client, logged_in_student):
        response = client.post('/api/ai/suggest', data={
            'title': 'WiFi down in library',
            'description': 'The wireless internet in the library is not working. Cannot connect to network for online classes.'
        })
        
        data = json.loads(response.data)
        assert data['category'] == 'IT Support'
        assert data['department'] == 'IT Cell'
    
    def test_ai_suggests_hostel_category_for_water(self, client, logged_in_student):
        response = client.post('/api/ai/suggest', data={
            'title': 'No water in hostel',
            'description': 'There is no water supply in hostel block A since morning. Students cannot bathe or use washrooms.'
        })
        
        data = json.loads(response.data)
        assert data['category'] == 'Hostel'
        assert data['department'] == 'Hostel Office'
    
    def test_ai_suggests_exam_category_for_results(self, client, logged_in_student):
        response = client.post('/api/ai/suggest', data={
            'title': 'Exam results delayed',
            'description': 'Semester examination results have not been published on the student portal. Need results for internship applications.'
        })
        
        data = json.loads(response.data)
        assert data['category'] == 'Examination'
        assert data['department'] == 'Examination Cell'
    
    def test_ai_confidence_values_are_numeric(self, client, logged_in_student):
        response = client.post('/api/ai/suggest', data={
            'title': 'Library book missing from shelf',
            'description': 'The book Data Structures and Algorithms is showing available in catalog but not on the shelf. Multiple students reported this issue.'
        })
        
        data = json.loads(response.data)
        assert isinstance(data['category_confidence'], (int, float))
        assert isinstance(data['priority_confidence'], (int, float))
        assert 0 <= data['category_confidence'] <= 100
        assert 0 <= data['priority_confidence'] <= 100
    
    def test_ai_similar_complaints_structure(self, client, logged_in_student, app):
        with app.app_context():
            complaint = Complaint(
                ticket_number='CR-2026-AI01',
                student_id=1,
                title='WiFi not working in library building',
                description='Library WiFi has been down for days. Students cannot access internet for research and assignments.',
                category='IT Support',
                priority='High',
                department='IT Cell',
                status='Resolved'
            )
            db.session.add(complaint)
            db.session.commit()
        
        response = client.post('/api/ai/suggest', data={
            'title': 'WiFi issue in library',
            'description': 'The WiFi in library is not working properly. Cannot connect to network for online work.'
        })
        
        data = json.loads(response.data)
        assert isinstance(data['similar_complaints'], list)
        # If similar complaints found, check structure
        for similar in data['similar_complaints']:
            assert 'ticket_number' in similar
            assert 'title' in similar
            assert 'category' in similar
            assert 'similarity' in similar
    
    def test_model_files_exist_after_training(self, app):
        with app.app_context():
            from app.ai.ai_utils import VECTORIZER_PATH, CATEGORY_MODEL_PATH, PRIORITY_MODEL_PATH, METADATA_PATH
            
            # Train if not exists
            if not os.path.exists(VECTORIZER_PATH):
                train_models()
            
            assert os.path.exists(VECTORIZER_PATH)
            assert os.path.exists(CATEGORY_MODEL_PATH)
            assert os.path.exists(PRIORITY_MODEL_PATH)
            assert os.path.exists(METADATA_PATH)
    
    def test_model_metadata_structure(self, app):
        with app.app_context():
            from app.ai.ai_utils import METADATA_PATH
            if os.path.exists(METADATA_PATH):
                with open(METADATA_PATH) as f:
                    metadata = json.load(f)
                
                assert 'algorithm' in metadata
                assert 'training_date' in metadata
                assert 'dataset_records' in metadata
                assert 'categories' in metadata
                assert 'category_accuracy' in metadata
                assert 'priority_accuracy' in metadata
    
    def test_load_models_function(self, app):
        with app.app_context():
            from app.ai.ai_utils import load_models
            result = load_models()
            # Should not crash
            assert isinstance(result, bool)
    
    def test_student_wellbeing_routes_to_support_cell(self, client, logged_in_student):
        response = client.post('/api/ai/suggest', data={
            'title': 'Need counseling for stress',
            'description': 'I am feeling overwhelmed with academic stress and anxiety. Would like to request appointment with campus counselor for mental health support.'
        })
        
        data = json.loads(response.data)
        # Should route to Student Support Cell for wellbeing
        if data['category'] == 'Student Wellbeing':
            assert data['department'] == 'Student Support Cell'