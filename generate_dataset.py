import pandas as pd
import random
from faker import Faker
import os

fake = Faker()
Faker.seed(42)
random.seed(42)

CATEGORIES = [
    'Hostel', 'IT Support', 'Library', 'Transport', 'Examination',
    'Fees and Accounts', 'Campus Facilities', 'Placement', 'Academics',
    'Student Wellbeing'
]

PRIORITIES = ['Critical', 'High', 'Medium', 'Low']

PRIORITY_KEYWORDS = {
    'Critical': [
        'urgent', 'emergency', 'immediate', 'critical', 'severe', 'crisis', 'dangerous',
        'safety hazard', 'health hazard', 'outage', 'down', 'not working', 'broken',
        'leaking', 'flooding', 'fire', 'accident', 'injury', 'toxic', 'contamination',
        'deadline today', 'deadline tomorrow', 'due today', 'due tomorrow', 'expires today',
        'stranded', 'trapped', 'unsafe', 'life threatening', 'medical emergency',
        'paper leak', 'ghosted', 'blacklist', 'ransom', 'data breach', 'hacked'
    ],
    'High': [
        'high priority', 'urgent attention', 'quickly', 'asap', 'soon', 'important',
        'affecting many', 'multiple students', 'widespread', 'ongoing for days',
        'reported before', 'not fixed', 'worsening', 'deteriorating', 'escalating',
        'missed classes', 'missing exams', 'cannot attend', 'preventing', 'blocking',
        'delayed', 'overdue', 'deadline approaching', 'need by', 'required for',
        'internship', 'placement', 'scholarship', 'graduation', 'results', 'grades'
    ],
    'Medium': [
        'medium priority', 'when possible', 'request', 'investigation needed',
        'improvement', 'enhancement', 'better', 'update', 'maintenance', 'repair',
        'replacement', 'not working properly', 'intermittent', 'sometimes', 'occasionally',
        'inconvenient', 'annoying', 'frustrating', 'would like', 'suggest', 'recommend',
        'feedback', 'complaint', 'issue', 'problem', 'concern', 'question', 'query'
    ],
    'Low': [
        'low priority', 'minor', 'small', 'cosmetic', 'nice to have', 'when convenient',
        'not urgent', 'no rush', 'whenever', 'eventually', 'someday', 'future',
        'suggestion', 'idea', 'feature request', 'enhancement request', 'nice if',
        'optional', 'not critical', 'not affecting', 'minor inconvenience', 'slightly',
        'a little', 'barely', 'hardly', 'rarely', 'once in a while'
    ],
}

DEPARTMENTS = {
    'Hostel': 'Hostel Office',
    'IT Support': 'IT Cell',
    'Library': 'Library',
    'Transport': 'Transport Office',
    'Examination': 'Examination Cell',
    'Fees and Accounts': 'Accounts Section',
    'Campus Facilities': 'Maintenance Department',
    'Placement': 'Placement Cell',
    'Academics': 'Academic Department / HOD',
    'Student Wellbeing': 'Student Support Cell',
}

LOCATIONS = {
    'Hostel': ['Hostel Block A', 'Hostel Block B', 'Hostel Block C', 'Hostel Block D', 'Hostel Block E', 'Hostel Block F', 'Hostel Block G', 'Hostel Block H', 'Hostel Block I', 'Hostel Block J', 'Hostel Mess', 'Hostel Common Room', 'Hostel Laundry', 'Hostel Study Room'],
    'IT Support': ['Library', 'IT Block', 'Computer Lab 1', 'Computer Lab 2', 'Computer Lab 3', 'Hostel Rooms', 'Online Portal', 'Campus Network', 'Placement Portal', 'Scholarship Portal'],
    'Library': ['Central Library', 'Department Library', 'Reference Section', 'Digital Library', 'Library Counter'],
    'Transport': ['Bus Route 1', 'Bus Route 2', 'Bus Route 3', 'Bus Route 4', 'Bus Route 5', 'Bus Route 6', 'Bus Route 7', 'Bus Route 8', 'Bus Route 9', 'Bus Route 10', 'Bus Route 11', 'Bus Route 12', 'Engineering Block Stop', 'Main Gate Stop', 'City Center Stop', 'Volvo Bus', 'Regular Bus'],
    'Examination': ['Examination Cell', 'Exam Hall 1', 'Exam Hall 2', 'Exam Hall 3', 'Academic Portal', 'Re-evaluation Section'],
    'Fees and Accounts': ['Accounts Section', 'Online Payment Portal', 'Scholarship Portal', 'Fee Counter', 'Bank'],
    'Campus Facilities': ['Engineering Block', 'Maintenance Department', 'Classroom 302', 'Computer Lab 2', 'Electronics Lab 1', 'Exam Hall 3', 'Lecture Hall 4', 'Badminton Courts', 'Gym', 'Canteen', 'Pathways', 'Main Campus Road', 'Water Coolers', 'Projectors', 'AC Units', 'Fans', 'Whiteboards'],
    'Placement': ['Placement Cell', 'Placement Portal', 'Mock Interview Hall', 'Company Visit Area'],
    'Academics': ['Academic Portal', 'Academic Department / HOD', 'Database Systems Class', 'Algorithms Class', 'Classroom 101', 'Lecture Hall'],
    'Student Wellbeing': ['Student Support Cell', 'Counselor Office', 'Wellness Center'],
}

TITLES = {
    'Hostel': [
        'Water supply issue in hostel', 'Mess food quality poor', 'Hostel room leaking ceiling',
        'Hostel laundry machines broken', 'Hostel WiFi frequent disconnection', 'Hostel water heater not working',
        'Hostel gate closing time', 'Hostel room allocation unfair', 'Hostel common room TV broken',
        'Hostel pest control needed', 'Hostel warden rude behavior', 'Hostel electricity fluctuation',
        'Hostel study room AC not working', 'Water pressure low in hostel', 'Mess hygiene concerns',
    ],
    'IT Support': [
        'WiFi not working', 'Scholarship portal error', 'Placement portal login issues',
        'Internet slow in hostel rooms', 'Library digital access not working', 'Fee payment portal down',
        'Library e-book access denied', 'Exam supplementary form error', 'Course registration system error',
        'Fee scholarship portal bug', 'Campus WiFi down', 'Email not working', 'Student portal error',
    ],
    'Library': [
        'Library book missing from shelves', 'Library fine incorrectly charged', 'Library timings too short',
        'Library book damaged', 'Library previous year papers', 'Library membership renewal',
        'Library new book requests', 'Library noise disturbance', 'Library magazine section',
        'Library newspaper subscription', 'Library seating insufficient', 'Library book not available',
    ],
    'Transport': [
        'Bus route delayed daily', 'Bus not stopping at designated stop', 'Transport safety issue',
        'Bus overcrowding', 'Bus schedule not updated', 'Bus timing for early classes',
        'Bus driver behavior rude', 'Bus GPS tracking not working', 'Bus route change not communicated',
        'Bus driver phone usage', 'Bus AC not working', 'Bus timing for night classes',
        'Transport strike affecting students',
    ],
    'Examination': [
        'Exam results not published', 'Exam hall seating not published', 'Exam re-evaluation pending',
        'Exam paper leak rumor', 'Exam hall AC not working', 'Exam schedule clash',
        'Exam invigilator misconduct', 'Exam hall seating uncomfortable', 'Exam answer key not released',
        'Exam marks not updated', 'Exam timetable clashes', 'Exam practical marks missing',
        'Exam supplementary form error',
    ],
    'Fees and Accounts': [
        'Fee receipt not generated after payment', 'Fee structure unclear', 'Scholarship delay',
        'Fee payment portal down', 'Fee concession not applied', 'Fee refund process slow',
        'Fee structure for foreign students', 'Fee receipt duplicate issue', 'Fee late fine excessive',
        'Fee installment option not available', 'Fee receipt for tax purpose', 'Fee scholarship portal bug',
    ],
    'Campus Facilities': [
        'Projector not working in classroom', 'AC not working in computer lab', 'Canteen hygiene concerns',
        'Sports equipment broken', 'Water cooler not working', 'Classroom chairs broken',
        'Campus lighting poor', 'Classroom whiteboard markers missing', 'Classroom fan not working',
        'Campus road potholes', 'Campus signage missing', 'Campus washroom hygiene',
        'Campus drinking water quality', 'Projector bulb replacement needed', 'Lab equipment not calibrated',
    ],
    'Placement': [
        'Placement portal login issues', 'Placement training inadequate', 'Placement cell unresponsive',
        'Placement offer letter delay', 'Placement salary data not shared', 'Placement mock interview scheduling',
        'Placement company blacklist request', 'Placement resume review not done', 'Placement internship opportunities',
        'Placement higher studies guidance', 'Placement alumni connect', 'Placement soft skills training',
    ],
    'Academics': [
        'Course registration system error', 'Professor not taking classes', 'Professor grading unfair',
        'Exam schedule clash', 'Syllabus not covered', 'Assignment deadline unrealistic',
        'Classroom overcrowded', 'Lab schedule conflict',
    ],
    'Student Wellbeing': [
        'Mental health counseling request', 'Counselor appointment delay', 'Stress management workshop request',
        'Peer support program inquiry', 'Disability accommodation request', 'Health insurance query',
    ],
}

DESCRIPTIONS = {
    'Hostel': [
        "Students are facing difficulties with basic needs. Issue ongoing for several days. Urgent attention needed.",
        "Multiple students affected. Health hazard if not resolved quickly. Need immediate investigation.",
        "Reported multiple times but no action taken. Condition worsening. Students uncomfortable.",
        "Affecting daily routine and academic performance. Need permanent solution not temporary fix.",
        "Safety concern for residents. Requesting urgent maintenance and inspection.",
    ],
    'IT Support': [
        "System throwing errors for past few days. Deadline approaching. Students unable to complete work.",
        "Multiple students reporting same issue. Affecting online classes and assignment submissions.",
        "Portal down since yesterday. Cannot access critical resources. Need immediate fix.",
        "Intermittent connectivity. Disconnects every few minutes. Cannot maintain stable session.",
        "Error 500 on submit. Happening consistently. Technical team needs to investigate.",
    ],
    'Library': [
        "Book shows available in catalog but not on shelf. Multiple students reported. Need to locate or replace.",
        "Returned book on time but system shows overdue. Have receipt. Fine incorrectly charged.",
        "Library closes too early during exam season. Students need extended hours for study.",
        "Received damaged book from library. Charged for damage but was already damaged when issued.",
        "Previous year question papers not available. Students cannot practice for upcoming exams.",
        "Newspapers not delivered for weeks. Missing current affairs for competitive exams.",
    ],
    'Transport': [
        "Bus consistently late every morning. Students miss first period classes. Schedule needs adjustment.",
        "Bus does not stop at designated stop. Students walk long distance. Specific driver ignores stop.",
        "Driver drives rashly. Overtakes dangerously. Students feel unsafe. Need driver training.",
        "Bus extremely overcrowded. Students hanging on doors. Safety hazard. Need additional bus.",
        "Schedule on website outdated. Buses running on old timings. Students missing buses.",
        "No bus for early morning classes. Students must take expensive auto. Need early bus.",
        "AC not working in buses. Unbearable heat. Students dehydrated.",
    ],
    'Examination': [
        "Results due last week but not on portal. Students need for internship applications.",
        "Seating arrangement not published. Students don't know exam halls and seat numbers.",
        "Applied for re-evaluation weeks ago. No update. Deadline passed. Need for GPA.",
        "Rumors of paper leak circulating. Need investigation to ensure fair examination.",
        "AC not working in exam hall. Temperature too high. Affects concentration during exam.",
        "Two core exams scheduled same time. Students cannot attend both. Need rescheduling.",
        "Invigilator helping certain students. Unfair advantage. Need investigation.",
        "Chairs in exam hall broken. Students back pain during 3-hour exams.",
        "Answer keys not released. Students cannot verify marks. Transparency needed.",
    ],
    'Fees and Accounts': [
        "Paid fees online. Payment successful but no receipt generated. Have transaction ID.",
        "Fee breakdown not transparent. Hidden charges appear. Need detailed fee structure document.",
        "Merit scholarship not disbursed. Economically weak students affected.",
        "Applied for fee concession but not reflected. Payment deadline approaching.",
        "Cancelled admission but refund not processed after 30 days. Policy says 15 days.",
        "Late fine excessive compared to other colleges. Need revision of fine structure.",
        "Need fee receipt with GST breakdown for income tax. Current receipt insufficient.",
    ],
    'Campus Facilities': [
        "Projector shows distorted colors and disconnects frequently. Affects all classes in room.",
        "Air conditioning not working. Room too hot for practical sessions. Multiple complaints.",
        "Food preparation area unhygienic. Seen pests near storage. Health hazard for students.",
        "Badminton courts have broken nets. Gym equipment rusted and unsafe. No maintenance for months.",
        "Water coolers not working. No drinking water on floor. Need repair or replacement.",
        "Many chairs in lecture hall broken. Students sitting on floor or standing. Need replacement.",
        "Pathways poorly lit. Unsafe at night. Need more streetlights for safety.",
        "No markers in any classroom. Teachers bringing own. Supply not replenished.",
        "Fans in multiple classrooms not working. Hot and stuffy. Cannot concentrate.",
        "Main campus road has large potholes. Vehicles damaged. Accidents happened. Urgent repair.",
        "No directional signs for departments. New students and visitors get lost.",
        "Washrooms unclean. No soap, broken taps. Basic hygiene not maintained.",
        "Water from coolers tastes metallic. Suspected contamination. Need water quality test.",
        "Projectors in multiple classrooms have dim bulbs. Hard to see slides.",
        "Oscilloscopes and function generators not calibrated for 6 months. Measurements inaccurate.",
    ],
    'Placement': [
        "Cannot login to placement portal with valid credentials. Shows invalid credentials error.",
        "Pre-placement training sessions basic. Not covering latest technologies. Students unprepared.",
        "Placement cell not responding to emails. No updates on company visits. Students anxious.",
        "Company gave verbal offer but written offer letter delayed. Students cannot plan.",
        "Placement cell not sharing salary packages. Need transparency for negotiation.",
        "Mock interviews scheduled during class hours. Students forced to choose. Need better scheduling.",
        "Request to blacklist company that ghosted students after selection. Wasted student time.",
        "Placement cell not reviewing resumes before company visits. Students sending poor resumes.",
        "No internship opportunities shared. Only final placement. Students need summer internships.",
        "No guidance for higher studies (GRE, GATE, CAT). Only job placement focus. Need balance.",
        "No alumni connect sessions. Alumni willing to mentor but no platform. Missed opportunity.",
        "Soft skills training too basic. Not industry-relevant. Need advanced communication training.",
    ],
    'Academics': [
        "System shows prerequisite not met for completed courses. Preventing registration for electives.",
        "Professor not taking classes for weeks. Syllabus behind. No substitute arranged.",
        "Professor grading inconsistently. Same answers get different marks. Need review.",
        "Multiple exam timetable clashes for elective subjects. Students cannot appear for all.",
    ],
    'Student Wellbeing': [
        "Request appointment with campus counselor for academic stress and anxiety. Feeling overwhelmed.",
        "Need professional guidance for stress management. Not an emergency but urgent.",
        "Interested in stress management workshop. When is next session?",
        "Looking for peer support program. How to join?",
        "Need disability accommodation for exams. What is the process?",
        "Query about student health insurance coverage. Need details.",
    ],
}

DURATION_BASE = {
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
}


def generate_complaint():
    category = random.choice(CATEGORIES)
    priority = random.choice(PRIORITIES)
    title_template = random.choice(TITLES[category])
    desc_template = random.choice(DESCRIPTIONS[category])
    
    location = random.choice(LOCATIONS[category])
    priority_keywords = random.sample(PRIORITY_KEYWORDS[priority], k=min(3, len(PRIORITY_KEYWORDS[priority])))
    
    title = f"{title_template} - {location}"
    description = f"{desc_template} Location: {location}. Priority indicators: {', '.join(priority_keywords)}. "
    
    base_duration = DURATION_BASE[category][priority]
    duration = max(1, base_duration + random.randint(-2, 3))
    
    return {
        'title': title,
        'description': description,
        'category': category,
        'priority': priority,
        'department': DEPARTMENTS[category],
        'resolution_time_days': duration,
        'location': location,
    }


def generate_dataset(num_samples=1000):
    data = []
    
    for _ in range(num_samples):
        data.append(generate_complaint())
    
    existing_df = pd.read_csv('data/sample_complaints.csv')
    for _, row in existing_df.iterrows():
        data.append({
            'title': row['title'],
            'description': row['description'],
            'category': row['category'],
            'priority': row['priority'],
            'department': row['department'],
            'resolution_time_days': row['resolution_time_days'],
            'location': '',
        })
    
    df = pd.DataFrame(data)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/extended_complaints.csv', index=False)
    print(f"Generated {len(df)} complaints")
    print(f"Categories: {df['category'].value_counts().to_dict()}")
    print(f"Priorities: {df['priority'].value_counts().to_dict()}")
    print(f"Avg duration: {df['resolution_time_days'].mean():.1f} days")
    
    return df


if __name__ == '__main__':
    generate_dataset(2000)