import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Test complaint submission flow
BASE_URL = 'http://127.0.0.1:5000'

session = requests.Session()

# 1. Get login page to get CSRF token
resp = session.get(f'{BASE_URL}/auth/login')
soup = BeautifulSoup(resp.text, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrf_token'})['value']

# 2. Login as student
login_data = {
    'csrf_token': csrf_token,
    'email': 'student01@campusresolve.demo',
    'password': 'Student@123',
    'remember_me': 'y'
}
resp = session.post(f'{BASE_URL}/auth/login', data=login_data, allow_redirects=False)
if resp.status_code == 302:
    resp = session.get(urljoin(BASE_URL, resp.headers.get('Location')))

# 3. Get the complaint form page to check CSRF token
resp = session.get(f'{BASE_URL}/student/complaints/new')
soup = BeautifulSoup(resp.text, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrf_token'})['value']

# 4. Get AI suggestions via API
ai_title = 'Water supply issue in hostel'
ai_description = 'No water in hostel block A since morning. Students cannot bathe or use washrooms. Urgent attention needed.'
resp = session.post(f'{BASE_URL}/api/ai/suggest', data={
    'csrf_token': csrf_token,
    'title': ai_title,
    'description': ai_description
})
ai_result = resp.json()
print(f'AI Suggest: {resp.status_code}')
print(f'Category: {ai_result["category"]} ({ai_result["category_confidence"]}%)')
print(f'Needs manual review: {ai_result["needs_manual_review"]}')

# 5. Verify the token - send CSRF in header
token = ai_result.get('verification_token')
verify_data = {
    'token': token,
    'title': ai_title,
    'description': ai_description
}
headers = {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrf_token
}
resp = session.post(f'{BASE_URL}/api/ai/verify', json=verify_data, headers=headers)
print(f'AI Verify: {resp.status_code}')
print(f'Verify Response: {resp.text}')

# 6. Submit complaint
if resp.status_code == 200:
    verify_result = resp.json()
    if verify_result.get('valid'):
        complaint_data = {
            'csrf_token': csrf_token,
            'title': ai_title,
            'description': ai_description,
            'category': ai_result['category'],
            'priority': ai_result['priority'],
            'location': 'Hostel Block A',
            'is_anonymous': 'false',
            'ai_verification_token': token,
            'ai_verified': 'true',
            'submit': 'Submit Complaint'
        }
        resp = session.post(f'{BASE_URL}/student/complaints/new', data=complaint_data, allow_redirects=False)
        print(f'Submit Complaint: {resp.status_code}')
        print(f'Redirect: {resp.headers.get("Location")}')
        if resp.status_code == 302:
            print('SUCCESS: Complaint submitted!')
        else:
            print('Response:', resp.text[:2000])