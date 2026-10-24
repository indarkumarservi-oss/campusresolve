from app import create_app
from app.ai.ai_utils import get_ai_suggestions

app = create_app()
with app.app_context():
    result = get_ai_suggestions(
        'Water leakage in hostel room',
        'There is a major water leakage in my hostel room 101 in Block A. Water is dripping from the ceiling and walls. The floor is completely wet and there is risk of electrical short circuit. This has been ongoing for 3 days and maintenance has not responded. Please send someone immediately to fix this.'
    )
    print('Cat:', result['category'], result['category_confidence'])
    print('Pri:', result['priority'], result['priority_confidence'])
    print('Needs manual:', result['needs_manual_review'])