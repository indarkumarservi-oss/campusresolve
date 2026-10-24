# CampusResolve

**AI-Assisted Student Grievance Classification, Tracking, and Resolution Management System**

A complete, locally deployable web application for college grievance management with role-based access control, AI-assisted complaint classification, and comprehensive tracking features.

## Recent Changes

- ✅ Removed command palette (⌘K) from UI
- ✅ Cleaned project structure (removed venv, __pycache__, .pytest_cache, test uploads)
- ✅ SQLite database persists permanently in `instance/campusresolve.db`

## Project Purpose

CampusResolve is a CSE mini-project demonstrating a full-stack grievance management system for educational institutions. It enables students to submit and track complaints, staff to manage assigned tickets, and administrators to oversee the entire resolution process with AI-powered suggestions.

## Key Features

### Student Features
- Submit complaints with title, description, category, priority, location, and attachments
- AI-assisted suggestions for category, priority, and department (advisory only)
- Track complaint status with visual timeline
- View assigned department, staff, and due dates
- Add follow-up comments while complaint is open
- Rate and provide feedback on resolved complaints
- In-app notifications with real-time updates
- Anonymous complaint option

### Staff Features
- Dashboard with assigned ticket counts (total, overdue, resolved)
- Filter assigned complaints by status and priority
- Update complaint status (In Progress, Pending Student Response, Resolved)
- Add action notes and internal notes
- Upload resolution evidence
- View status history and comments

### Admin Features
- Complete oversight of all complaints
- Review and edit complaint details (category, priority, department)
- Assign/reassign staff members
- Set due dates and update any status
- Mark complaints as duplicates and link to parent tickets
- Full audit trail and status history
- User management (create, edit, activate/deactivate)
- Export filtered complaints to CSV
- Comprehensive analytics with Chart.js visualizations
- Create notifications on assignment/status changes

### AI/ML Features
- Offline NLP pipeline using scikit-learn (TF-IDF + LogisticRegression)
- Predicts complaint category, priority, and suggested department
- Confidence scores for all predictions
- Finds similar previous complaints using cosine similarity
- Keyword-based explanation for predictions
- Advisory only - admin has final control
- No external API calls - runs completely offline

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, Flask 3.0 |
| Database | SQLite (default), SQLAlchemy ORM |
| Authentication | Flask-Login, Werkzeug password hashing |
| Forms | Flask-WTF, WTForms |
| Frontend | HTML5, CSS3, Bootstrap 5 (CDN), Chart.js (CDN) |
| ML/AI | scikit-learn, pandas, joblib |
| Testing | pytest, pytest-flask |
| Deployment | Local development server |

## Folder Structure

```
campusresolve/
├── run.py                 # Application entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── .gitignore             # Git ignore rules
├── seed.py                # Database seeding script
├── train_model.py         # ML model training script
├── app/                   # Main application package
│   ├── __init__.py        # App factory & extensions
│   ├── extensions.py      # Flask extensions (db, login, csrf)
│   ├── models/            # SQLAlchemy models
│   │   ├── __init__.py
│   │   └── models.py
│   ├── forms/             # WTForms definitions
│   │   ├── __init__.py
│   │   └── forms.py
│   ├── ai/                # AI/ML utilities
│   │   ├── __init__.py
│   │   └── ai_utils.py
│   ├── auth/              # Authentication blueprint
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── student/           # Student blueprint
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── staff/             # Staff blueprint
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── admin/             # Admin blueprint
│   │   ├── __init__.py
│   │   └── routes.py
│   └── api/               # API endpoints blueprint
│       ├── __init__.py
│       └── routes.py
├── instance/
│   ├── campusresolve.db   # SQLite database (persistent)
│   └── uploads/           # File uploads directory
├── data/
│   └── sample_complaints.csv  # Training data (120+ records)
├── models/
│   ├── vectorizer.joblib        # TF-IDF vectorizer
│   ├── category_model.joblib    # Category classifier
│   ├── priority_model.joblib    # Priority classifier
│   └── model_metadata.json      # Model metadata
├── tests/
│   ├── conftest.py          # Pytest fixtures
│   ├── test_auth.py         # Authentication tests
│   ├── test_complaints.py   # Complaint workflow tests
│   ├── test_permissions.py  # Authorization tests
│   ├── test_ai.py           # AI functionality tests
│   └── test_dashboard.py    # Dashboard tests
├── templates/
│   ├── base.html            # Base template
│   ├── auth/login.html      # Login page
│   ├── public/home.html     # Home page
│   ├── student/             # Student templates
│   ├── staff/               # Staff templates
│   ├── admin/               # Admin templates
│   └── errors/              # Error pages (403, 404)
└── static/
    ├── css/style.css        # Custom styles (dark mode, animations)
    ├── js/app.js            # Frontend JavaScript
    └── img/logo-placeholder.svg  # Logo
```

**Note:** `venv/`, `__pycache__/`, `.pytest_cache/` are generated at runtime and excluded via `.gitignore`.

## Setup Instructions

### Prerequisites
- Python 3.11 or higher
- pip (Python package manager)

### Windows Setup (PowerShell)

```powershell
# 1. Navigate to project directory
cd campusresolve

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
.\venv\Scripts\Activate.ps1
# If script execution fails, run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 4. Install dependencies
pip install -r requirements.txt

# 5. Train ML models
python train_model.py

# 6. Seed database with demo data
python seed.py

# 7. Run the application
python run.py
```

### Linux/macOS Setup

```bash
# 1. Navigate to project directory
cd campusresolve

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate virtual environment
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Train ML models
python train_model.py

# 6. Seed database with demo data
python seed.py

# 7. Run the application
python run.py
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `python train_model.py` | Train ML models from sample data |
| `python seed.py` | Initialize database and seed demo data |
| `python run.py` | Start development server on port 5000 |
| `pytest -q` | Run test suite quietly |
| `pytest -v` | Run tests with verbose output |

## Local Network Demo

To demonstrate on classmates' phones via local Wi-Fi/hotspot:

1. **Start the server on all interfaces:**
   ```bash
   python run.py
   # Server runs on http://0.0.0.0:5000
   ```

2. **Find your laptop's local IP:**
   - **Windows:** `ipconfig` (look for IPv4 Address under Wi-Fi)
   - **Linux:** `ip addr show` or `hostname -I`
   - **macOS:** `ifconfig` or `ipconfig getifaddr en0`

3. **Access from phones on same network:**
   ```
   http://<YOUR_LAPTOP_IP>:5000
   # Example: http://192.168.1.45:5000
   ```

4. **Firewall note (Windows):**
   - Allow Python through Windows Defender Firewall for Private networks
   - Or run: `netsh advfirewall firewall add rule name="Flask 5000" dir=in action=allow protocol=TCP localport=5000`

## Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| **Admin** | admin@campusresolve.demo | Admin@123 |
| **Staff (Hostel)** | hostel.staff@campusresolve.demo | Staff@123 |
| **Staff (IT)** | it.staff@campusresolve.demo | Staff@123 |
| **Staff (Maintenance)** | maintenance.staff@campusresolve.demo | Staff@123 |
| **Student 1** | student01@campusresolve.demo | Student@123 |
| **Student 2** | student02@campusresolve.demo | Student@123 |
| **Student 3** | student03@campusresolve.demo | Student@123 |

## Live Demo Script for Viva

1. **Student submits complaint:**
   - Login as `student01@campusresolve.demo` / `Student@123`
   - Click "Raise New Complaint"
   - Fill title: "WiFi not working in library"
   - Fill description: "The WiFi in the main library has been down for two days..."
   - Click "Get AI Suggestions" → shows category: IT Support, priority: High, department: IT Cell
   - Accept suggestions and submit

2. **Admin reviews and assigns:**
   - Login as `admin@campusresolve.demo` / `Admin@123`
   - View complaint in "All Complaints"
   - Click complaint → see AI suggestions panel
   - Assign to IT Staff, set due date, change status to "Assigned"

3. **Staff updates complaint:**
   - Login as `it.staff@campusresolve.demo` / `Staff@123`
   - See assigned complaint on dashboard
   - Update status to "In Progress" with action note
   - Later update to "Resolved" with evidence upload

4. **Student tracks and gives feedback:**
   - Login as student
   - View complaint → see status timeline
   - After "Resolved", submit 5-star feedback

5. **Admin shows analytics:**
   - Login as admin
   - Visit Analytics page → view charts by category, status, priority, monthly trends
   - Export complaints as CSV

## Responsible AI & Privacy

- **No external data transmission** - All ML runs locally
- **No personal data in ML features** - Only complaint text is used
- **Advisory only** - AI suggestions require admin confirmation
- **No automated rejections** - System never auto-rejects complaints
- **No discriminatory predictions** - No mental health diagnoses or risk labels
- **Student Wellbeing handling** - Routes to Student Support Cell with neutral messaging
- **Demo data only** - All accounts and complaints are fictional

## Known Limitations

- **Local demo only** - Not production-ready (no HTTPS, no rate limiting, SQLite limitations)
- **Fake data only** - All complaints and users are fictional
- **AI requires human review** - Confidence threshold 60%, below that shows "Needs manual review"
- **SQLite for demo** - Suitable for single-user demo, not concurrent multi-user production
- **No email/SMS notifications** - In-app only
- **Single instance** - No horizontal scaling
- **Development server** - Use Gunicorn/uWSGI for production

## Troubleshooting

### Port 5000 Already in Use
```bash
# Find process using port 5000
# Windows: netstat -ano | findstr :5000
# Linux/macOS: lsof -i :5000

# Kill process (Windows)
taskkill /PID <PID> /F

# Kill process (Linux/macOS)
kill -9 <PID>

# Or change port in run.py: app.run(port=5001)
```

### Model Files Missing
```bash
python train_model.py
```

### Database Missing / Corrupted
```bash
# Delete database and reseed
del campusresolve.db  # Windows
rm campusresolve.db   # Linux/macOS
python seed.py
```

### Phone Cannot Access Laptop IP
- Ensure both devices on same Wi-Fi/hotspot
- Check laptop firewall allows port 5000
- Try `http://<IP>:5000` (not https)
- Disable VPN on laptop if active
- Check laptop IP hasn't changed (DHCP)

### Firewall Issues (Windows)
```powershell
# Allow Python through firewall
New-NetFirewallRule -DisplayName "Flask Dev Server" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

### Import Errors / Module Not Found
```bash
# Ensure virtual environment is activated
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

## Test Results

Run the test suite:
```bash
pytest -q
```

Expected output (all tests passing):
```
.................................................................        [100%]
65 passed in ~16s
```

### Test Coverage
- **Authentication:** Login success/failure, logout, registration, password hashing
- **Authorization:** Role-based access control, cross-role restrictions, anonymous complaints
- **Complaint Workflow:** Create, assign, status transitions, feedback, ticket generation, attachments
- **AI/ML:** Suggestion endpoint, confidence values, similar complaints, model files, metadata
- **Dashboards:** All role dashboards load with correct data, analytics, notifications
- **Security:** Password hashing, file upload validation, CSV export protection, CSRF

## Development

### Adding New Features
1. Create model changes in `app/models/models.py`
2. Add forms in `app/forms/forms.py`
3. Add routes in appropriate blueprint (`app/student/routes.py`, `app/staff/routes.py`, `app/admin/routes.py`)
4. Create templates in `templates/<role>/`
5. Add tests in `tests/`
6. Run `pytest` to verify

### Resetting Demo Database
```bash
python seed.py
# Script drops and recreates all tables
```

### Retraining Models
```bash
# Modify data/sample_complaints.csv then:
python train_model.py
```

## License

This is an academic demonstration project for educational purposes. All code is free and open-source.

## Credits

Built as a CSE Mini Project using:
- Flask, SQLAlchemy, Flask-Login, Flask-WTF
- scikit-learn, pandas, joblib
- Bootstrap 5, Chart.js
- pytest for testing

---

**CampusResolve** — FOR AIET CSE Mini Project Demonstration#   c a m p u s r e s o l v e  
 