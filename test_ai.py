from app import create_app
from app.ai.ai_utils import get_ai_suggestions, verify_verification_token

app = create_app()
with app.app_context():
    result = get_ai_suggestions('WiFi not working in library', 'The WiFi in the main library has been down for two days and students cannot access online resources.')
    print('Category:', result['category'])
    print('Priority:', result['priority'])
    print('Department:', result['department'])
    print('Token:', result['verification_token'][:50] if result['verification_token'] else None)
    vr = verify_verification_token(result['verification_token'], 'WiFi not working in library', 'The WiFi in the main library has been down for two days and students cannot access online resources.')
    print('Verify:', vr)