# 🧬 Epidemic Monitoring System

A Flask-based web application that enables users to upload, visualize, analyze, and share epidemic-related datasets (CSV, Excel, or JSON). It includes secure user authentication with OTP verification, role-based sharing, dynamic mapping, and statistical dashboards.

This system emphasizes:
- Performance via batch uploads & background parsing
- Security via OTP login and 2FA
- Insight via mapping (Leaflet) & trends (Chart.js)
----------------------------------------------------------------------------------------------------

## Features

- ✅ **User Authentication**
  - Sign up with email verification (OTP via email or SMS)
  - Login/Logout with secure password hashing
  - Password reset functionality

- ✅ **Profile Management**
  - Editable profile with fields like full name, DOB, location, and profile picture
  - Accounts Settings to update Email address and Timezone
  - Security Settings like changing password
  - Notification Settings to manage Alerts
  - Data Management settings allow users to control retention, export, and permanent deletion of their datasets and account data for privacy and lifecycle management

- ✅ **Data Upload & Ingestion**
  - Supports `.csv`, `.json`, `.xlsx`, `.xls` file formats
  - Automatic format detection and field standardization

- ✅ **Data Visualization**
  - Leaflet-based geospatial map
  - Chart.js-based trend analysis
  - Tabular preview of uploaded datasets


- ✅ **Data Sharing & Access Control**
  - Share datasets with other users (read/download permission)
  - Public/private dataset visibility toggles

- ✅ **Analytics Dashboard**
  - Statistical summaries
  - Top affected locations
  - Download insights as CSV

- ✅ **Audit Logging**
  - Tracks actions like login, signup, upload, and deletion

- ✅ **Responsive UI**
  - Clean and modern design with Bootstrap 5 and custom JavaScript modules

----------------------------------------------------------------------------------------------------

## Tech Stack

| Layer         | Technology                              |
|--------------|------------------------------------------|
| Framework     | Flask, Flask-Login, Flask-WTF, Flask-Migrate |
| Backend       | Python 3.9+, SQLite (default)            |
| Frontend      | HTML, Bootstrap 5, Leaflet, Chart.js     |
| ORM           | SQLAlchemy                               |
| Forms         | WTForms                                  |
| Email         | Flask-Mail (SMTP)                        |
| OTP Delivery  | `pyotp` for TOTP, Twilio for SMS         |
| File Handling | Pandas, NumPy, tqdm                      |

---

## Folder Structure
Agile_Web_Development/
├── __init__.py
├── app.py
├── data_bridge.py
├── forms.py
├── models.py
├── utils.py
├── README.md
├── requirements.txt
├── .gitignore
├── .venv/
├── .pytest_cache/
├── __pycache__/
├── assets/
│   └── ERD.jpg
├── instance/
│   └── .gitkeep
├── migrations/
│   ├── versions/
│   ├── alembic.ini
│   ├── env.py
│   ├── README
│   └── script.py.mako
├── blueprints/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── data/
│   │   ├── __init__.py
│   │   └── routes.py
│   └── profile/
│       ├── __init__.py
│       └── routes.py
├── static/
│   ├── css/
│   │   ├── charts.css
│   │   ├── map.css
│   │   ├── style.css
│   │   └── table-style.css
│   ├── js/
│   │   ├── charts.js
│   │   ├── Insight-generator.js
│   │   ├── loading.js
│   │   ├── map.js
│   │   ├── submission-handler.js
│   │   └── theme-toggle.js
│   ├── data/
│   └── uploads/
├── templates/
│   ├── base.html
│   ├── charts.html
│   ├── dashboard.html
│   ├── debug_file.html
│   ├── edit_profile.html
│   ├── explore.html
│   ├── forgot_password.html
│   ├── help.html
│   ├── home.html
│   ├── index.html
│   ├── login.html
│   ├── map-test.html
│   ├── profile.html
│   ├── reset_password.html
│   ├── reset_success.html
│   ├── settings.html
│   ├── signup.html
│   ├── upload.html
│   ├── verify_otp.html
│   └── visualize.html
├── tests/
│   ├── test_basics.py
│   └── sys_test/
│       ├── conftest.py
│       ├── run_tests.py
│       ├── signup_form.png
│       ├── test_auth.py
│       ├── test_dashboard.py
│       ├── test_upload.py
│       └── test_visualization.py
│── __init__.py
├── .gitignore                  # Git ignored files
├── app.py                      # Main Flask application
├── data_bridge.py              # Data I/O and transformation logic
├── forms.py                    # Flask-WTF forms definitions
├── models.py                   # SQLAlchemy models for database schema
├── README.md                   # Project documentation
├── requirements.txt            # Python package dependencies
└── utils.py                    # Utility functions



## Installation
```bash
git clone https://github.com/NandhiniSrinivasan24251813/Agile_Web_Development
cd epidemic-monitoring

python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

pip install -r requirements.txt


## Initialize the database
flask db init
flask db migrate
flask db upgrade
 

## Run the development server

flask run 
python app.py

```

## System tests

```
pytest -v 
```
for system tests(login/signup/checking dashboard.etc)


## Sample User Flow
1. User signs up → receives OTP on email → logs in.
2. Uploads dataset → auto-detected fields & date ranges.
3. Views data on map → filters by cases, deaths, recovered.
4. Shares dataset with another user via email lookup.
5. Downloads insights as CSV and JSON.

## Contributors

| UWA ID   | Name               | GitHub Username         |
|----------|--------------------|--------------------------|
| 24251813 | Nandhini Srinivasan| Nandhini Srinivasan      |
| 24476099 | Harpreet Singh     | harpreet12345678singh    |
| 24060283 | Swapnil Gaikwad    | SwapyG                   |
| 23911598 | Terran Deng        | TerranConfederacy        |
