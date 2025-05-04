from flask import Flask, render_template, redirect, send_file, url_for, flash, request
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from models import db, User, AuditLog
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
from flask_migrate import Migrate

from models import db, User, AuditLog, PasswordResetToken, Dataset, EpidemicRecord, SharedDataset
import secrets
from forms import EditProfileForm
from werkzeug.utils import secure_filename
import os
import pandas as pd
import numpy as np
import json
import io


# Initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///epidemic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['DATA_FOLDER'] = os.path.join('static', 'data')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# folders setup
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)

db.init_app(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --------------------------------------------
# Routes
# --------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('signup.html')

        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('signup.html')

        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()

            # Insert into AuditLog
            audit = AuditLog(
                user_id=new_user.id,
                action="signup",
                target_type="User",
                target_id=new_user.id,
                details=f"User {new_user.username} signed up"
            )
            db.session.add(audit)
            db.session.commit()

            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'error')
            print(f"Error during signup: {str(e)}")

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember_me' in request.form

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)

            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()

            # Insert into AuditLog
            audit = AuditLog(
                user_id=user.id,
                action="login",
                target_type="User",
                target_id=user.id,
                details=f"User {user.username} logged in"
            )
            db.session.add(audit)
            db.session.commit()

            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))



#Forgot Password
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')

        # Find user by email
        user = User.query.filter_by(email=email).first()

        if user:
            # If user exists, generate reset token
            token = secrets.token_hex(32)

            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow()
            )
            db.session.add(reset_token)
            db.session.commit()

            # Generate reset link
            reset_link = url_for('reset_password', token=token, _external=True)
            flash(f'Password reset link: {reset_link}', 'info')

            # Audit Log
            audit = AuditLog(
                user_id=user.id,
                action="forgot_password",
                target_type="User",
                target_id=user.id,
                details="Password reset requested"
            )
            db.session.add(audit)
            db.session.commit()

            return redirect(url_for('forgot_password'))
        else:
            # If email not found
            flash('Email address not found. Please check and try again.', 'error')
            return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')


## Reset Password
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = PasswordResetToken.query.filter_by(token=token).first()

    if not reset_token:
        flash('Invalid or expired token', 'error')
        return redirect(url_for('login'))

    user = User.query.get(reset_token.user_id)

    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html', token=token)

        # Update user's password
        user.set_password(new_password)
        db.session.delete(reset_token)  # remove used token
        db.session.commit()

        # Audit Log
        audit = AuditLog(
            user_id=user.id,
            action="reset_password",
            target_type="User",
            target_id=user.id,
            details="Password reset successfully"
        )
        db.session.add(audit)
        db.session.commit()

        flash('Password reset successful.', 'success')
        return redirect(url_for('reset_success'))


    return render_template('reset_password.html', token=token)

@app.route('/reset_success')
def reset_success():
    return render_template('reset_success.html')


# Profile
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(obj=current_user)

    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.work_location = form.work_location.data  # renamed from location
        current_user.bio = form.bio.data
        current_user.dob = form.dob.data
        current_user.mobile = form.mobile.data
        current_user.address = form.address.data
        current_user.postcode = form.postcode.data
        current_user.city = form.city.data
        current_user.last_seen = datetime.utcnow()

        if form.profile_picture.data:
            picture_file = secure_filename(form.profile_picture.data.filename)
            picture_path = os.path.join(app.config['UPLOAD_FOLDER'], picture_file)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            form.profile_picture.data.save(picture_path)
            current_user.profile_picture = picture_file

        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', form=form)





@app.route('/dashboard')
@login_required
def dashboard():
    # Quickfix 02/05/2025: Get datasets for the current user
    user_datasets = Dataset.query.filter_by(user_id=current_user.id).order_by(Dataset.upload_date.desc()).all()
    
    # Print for debugging
    print(f"Found {len(user_datasets)} datasets for user {current_user.username}")
    
    # Later!
    shared_datasets = []  # Later!
    
    return render_template('dashboard.html', 
                          user_datasets=user_datasets,
                          shared_datasets=shared_datasets)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        # Check if file was included
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
            
        file = request.files['file']
        
        # Check if a file was selected
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
            
        # Validate file extension
        if file and allowed_file(file.filename):
            # Get form data
            name = request.form.get('name')
            description = request.form.get('description')
            data_type = request.form.get('data_type', 'cases')
            sharing_status = request.form.get('sharing_status', 'private')
            has_geo = 'has_geo' in request.form
            has_time = 'has_time' in request.form
            
            # Save file with timestamp to avoid name collisions
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            file_path = os.path.join(app.config['DATA_FOLDER'], f"{timestamp}_{filename}")
            file.save(file_path)
            
            try:
                # Process the file
                df = None
                
                # Load based on file type
                if filename.endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif filename.endswith('.json'):
                    df = pd.read_json(file_path)
                elif filename.endswith('.xlsx') or filename.endswith('.xls'):
                    df = pd.read_excel(file_path)
                else:
                    flash('Unsupported file format', 'error')
                    return redirect(request.url)
                
                # Get record count
                record_count = len(df)
                
                # Auto-detect geographic data if not explicitly set
                lat_col = None
                lon_col = None
                
                for col in df.columns:
                    col_lower = col.lower()
                    if col_lower in ['latitude', 'lat']:
                        lat_col = col
                    elif col_lower in ['longitude', 'long', 'lon', 'lng']:
                        lon_col = col
                
                # Update has_geo based on detected columns
                has_geo = has_geo or (lat_col is not None and lon_col is not None)
                
                # Auto-detect time series data if not explicitly set
                date_col = None
                date_range_start = None
                date_range_end = None
                
                for col in df.columns:
                    col_lower = col.lower()
                    if 'date' in col_lower or 'time' in col_lower or 'day' in col_lower:
                        date_col = col
                        break
                
                # Process date data if found
                if date_col:
                    try:
                        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                        valid_dates = df[date_col].dropna()
                        
                        if not valid_dates.empty:
                            date_range_start = valid_dates.min().date()
                            date_range_end = valid_dates.max().date()
                            has_time = True
                    except Exception as e:
                        # If date conversion fails, log but continue
                        print(f"Error converting dates: {e}")
                
                # Create dataset record
                new_dataset = Dataset(
                    name=name,
                    description=description,
                    filename=filename,
                    filepath=file_path,
                    file_type=data_type,
                    record_count=record_count,
                    date_range_start=date_range_start,
                    date_range_end=date_range_end,
                    has_geo=has_geo,
                    has_time=has_time,
                    sharing_status=sharing_status,
                    user_id=current_user.id,
                    upload_date=datetime.utcnow()
                )
                
                db.session.add(new_dataset)
                db.session.commit()
                
                # Log the upload
                audit = AuditLog(
                    user_id=current_user.id,
                    action="upload",
                    target_type="Dataset",
                    target_id=new_dataset.id,
                    details=f"User uploaded dataset: {name}"
                )
                db.session.add(audit)
                db.session.commit()
                
                flash('Dataset uploaded successfully!', 'success')
                return redirect(url_for('dashboard'))
                
            except Exception as e:
                # If there's an error, log and report back to user
                db.session.rollback()
                flash(f'Error processing file: {str(e)}', 'error')
                print(f"Error processing upload: {str(e)}")
                return redirect(request.url)
        else:
            flash('Invalid file type. Allowed types: CSV, JSON, Excel', 'error')
            return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/visualize/<int:dataset_id>')
@login_required
def visualize(dataset_id):
    # Get dataset
    dataset = Dataset.query.get_or_404(dataset_id)
    
    # Check if user has access
    is_owner = dataset.user_id == current_user.id
    is_shared = False  # We'll implement sharing later
    is_public = dataset.sharing_status == 'public'
    
    if not (is_owner or is_shared or is_public):
        flash('You do not have access to this dataset', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Load dataset file
        df = None
        
        if dataset.filepath and os.path.exists(dataset.filepath):
            if dataset.filename.endswith('.csv'):
                df = pd.read_csv(dataset.filepath)
            elif dataset.filename.endswith('.json'):
                df = pd.read_json(dataset.filepath)
            elif dataset.filename.endswith('.xlsx') or dataset.filename.endswith('.xls'):
                df = pd.read_excel(dataset.filepath)
        else:
            flash('Dataset file not found', 'error')
            return redirect(url_for('dashboard'))
        
        # Prepare map data
        map_data = []
        
        if dataset.has_geo:
            # Find lat/lon columns
            lat_col = next((col for col in df.columns if col.lower() in ['latitude', 'lat']), None)
            lon_col = next((col for col in df.columns if col.lower() in ['longitude', 'long', 'lon', 'lng']), None)
            
            if lat_col and lon_col:
                # Create map data dictionary
                for _, row in df.iterrows():
                    if pd.notna(row[lat_col]) and pd.notna(row[lon_col]):
                        point = {}
                        for col in df.columns:
                            # For each column, add to point if not null
                            if pd.notna(row[col]):
                                # Convert numpy values to native Python types for JSON
                                if isinstance(row[col], (pd.Timestamp, np.datetime64)):
                                    point[col] = row[col].strftime('%Y-%m-%d')
                                elif isinstance(row[col], (np.int64, np.int32, np.float64, np.float32)):
                                    point[col] = float(row[col])
                                else:
                                    point[col] = row[col]
                        map_data.append(point)
        
        # Get sample data for preview
        preview_data = df.head(5).to_dict('records')
        preview_columns = df.columns.tolist()
        
        # Get numeric fields for charts
        numeric_fields = df.select_dtypes(include=[np.number]).columns.tolist()
        
        return render_template('visualize.html',
                              dataset=dataset,
                              preview_data=preview_data,
                              preview_columns=preview_columns,
                              map_data=json.dumps(map_data),
                              numeric_fields=numeric_fields)
    
    except Exception as e:
        flash(f'Error processing dataset: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Simple Export Route
@app.route('/export/<int:dataset_id>')
@login_required
def export_dataset(dataset_id):
    # Get dataset
    dataset = Dataset.query.get_or_404(dataset_id)
    
    # Check permission
    is_owner = dataset.user_id == current_user.id
    is_shared = False  # We'll implement sharing later
    is_public = dataset.sharing_status == 'public'
    
    if not (is_owner or is_shared or is_public):
        flash('You do not have access to this dataset!!!', 'error')
        return redirect(url_for('dashboard'))
    
    # Get export format
    export_format = request.args.get('format', 'csv')
    
    try:
        # Load the file
        df = None
        
        if dataset.filepath and os.path.exists(dataset.filepath):
            if dataset.filename.endswith('.csv'):
                df = pd.read_csv(dataset.filepath)
            elif dataset.filename.endswith('.json'):
                df = pd.read_json(dataset.filepath)
            elif dataset.filename.endswith('.xlsx') or dataset.filename.endswith('.xls'):
                df = pd.read_excel(dataset.filepath)
        else:
            flash('Dataset file not found', 'error')
            return redirect(url_for('dashboard'))
        
        # Export based on format
        if export_format == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f"{dataset.name}_export.csv"
            )
        
        elif export_format == 'json':
            output = io.StringIO()
            df.to_json(output, orient='records')
            output.seek(0)
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='application/json',
                as_attachment=True,
                download_name=f"{dataset.name}_export.json"
            )
        
        else:
            flash('Unsupported export format', 'error')
            return redirect(url_for('visualize', dataset_id=dataset_id))
            
    except Exception as e:
        flash(f'Error exporting dataset: {str(e)}', 'error')
        return redirect(url_for('visualize', dataset_id=dataset_id))

# --------------------------------------------
# Helper Functions
# --------------------------------------------
def allowed_file(filename):
    """Check if the file has an allowed extension"""
    ALLOWED_EXTENSIONS = {'csv', 'json', 'xlsx', 'xls'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# --------------------------------------------
# Main
# --------------------------------------------
if __name__ == '__main__':
    # with app.app_context():
    #     db.create_all()
    # using migrate instead of create_all to handle db migrations
    app.run(debug=True, host='0.0.0.0', port=8080)





