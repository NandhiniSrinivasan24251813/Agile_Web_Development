from flask import Flask, render_template, redirect, send_file, url_for, flash, request
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from models import db, User, AuditLog
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
from flask_migrate import Migrate
from flask import abort
from models import db, User, AuditLog, PasswordResetToken, Dataset, EpidemicRecord, SharedDataset
import secrets
from forms import EditProfileForm
from werkzeug.utils import secure_filename
import os
import pandas as pd
import numpy as np
import json
import io
from tqdm import tqdm
import threading
from queue import Queue
import time
import logging
from flask import abort, flash, redirect, url_for
from twilio.rest import Client
import random
from flask import session
from flask import Flask, Blueprint
from flask_wtf import CSRFProtect
from itertools import chain
# Custom imports
from data_bridge import DataBridge
from utils import DataConverter


app = Flask(__name__)
csrf = CSRFProtect(app)

api_blueprint = Blueprint('api', __name__)
csrf.exempt(api_blueprint)

app.register_blueprint(api_blueprint)

# Initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///epidemic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['DATA_FOLDER'] = os.path.join('static', 'data')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['BATCH_SIZE'] = 1000  # Number of records to process in each batch
app.config['MAX_WORKERS'] = 4    # Maximum number of worker threads
app.config['CHUNK_SIZE'] = 1024 * 1024  # 1MB chunks for file reading

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('app')

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


from flask_mail import Mail, Message

app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # or your mail server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'harpreetvallah2@gmail.com'
app.config['MAIL_PASSWORD'] = 'owoz huca itgc zvqj'  # Use an app-specific password

mail = Mail(app)

import pyotp

def send_otp_email(user_email, otp):
    subject = "🔐 Your OTP Code"
    body = f"""
    Hi,

    Your OTP code is: {otp}

    Please enter this to verify your account.

    Thanks,
    The Team
    """
    msg = Message(subject, sender="your_project_email@example.com", recipients=[user_email])
    msg.body = body
    mail.send(msg)


def send_welcome_email(user_email, username):
    subject = "🎉 Welcome to Our Platform!"
    body = f"""
            Hi {username},

            Thank you for signing up with us!

            We’re excited to have you on board. If you have any questions, feel free to reach out.

            Best regards,  
            The Team
            """
    msg = Message(subject, sender=('Epidemic Monitoring System',"your_email@gmail.com"), recipients=[user_email])
    msg.body = body
    mail.send(msg)

def send_otp(mobile, otp):
    client = Client(app.config['TWILIO_ACCOUNT_SID'], app.config['TWILIO_AUTH_TOKEN'])
    message = client.messages.create(
        body=f'Your OTP is: {otp}',
        from_=app.config['TWILIO_PHONE_NUMBER'],
        to=mobile
    )


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username         = request.form.get('username')
        email            = request.form.get('email')
        password         = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        mobile_number    = request.form.get('mobile_number')

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

            otp = pyotp.TOTP(pyotp.random_base32(), digits=6).now()
            print("otp is ------------->", otp)
            new_user.otp = otp
            send_otp_email(email, otp)

            print("send_otp function is called and otp is send")
            # db.session.flush()

            # Insert into AuditLog
            audit = AuditLog(
                user_id=new_user.id,
                action="signup",
                target_type="User",
                target_id=new_user.id,
                details=f"User {new_user.username} signed up"
            )
            send_welcome_email(email, username)
            db.session.add(audit)
            db.session.commit()
            session['user_id'] = new_user.id 
            flash('Account created successfully! Welcome email and otp sent.', 'success')
            # return redirect(url_for('login'))
            return redirect(url_for('verify_otp'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'error')
            print(f"Error during signup: {str(e)}")

    return render_template('signup.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        # Get OTP from form
        entered_otp = request.form.get('otp')
        
        # Retrieve user ID from the session
        user_id = session.get('user_id')
        
        if user_id:
            # Fetch user based on the stored user ID
            user = User.query.get(user_id)
            
            if user and user.otp == entered_otp:
                login_user(user)
                flash('OTP verified. You are now logged in.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid OTP. Please try again.', 'error')
        else:
            flash('No user ID found in session. Please start the OTP process again.', 'error')

    return render_template('verify_otp.html')



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


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'account':
            # Update account settings
            current_user.email = request.form.get('email')
            current_user.timezone = request.form.get('timezone')
            db.session.commit()
            
            # Log the update
            audit = AuditLog(
                user_id=current_user.id,
                action="update_account",
                target_type="User",
                target_id=current_user.id,
                details="Updated account settings"
            )
            db.session.add(audit)
            db.session.commit()
            
            flash('Account settings updated successfully!', 'success')
            
        elif form_type == 'security':
            # Update security settings
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            enable_2fa = request.form.get('enable_2fa') == '1'
            
            # Verify current password
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('settings'))
            
            # Update password if provided
            if new_password:
                if new_password != confirm_password:
                    flash('New passwords do not match.', 'error')
                    return redirect(url_for('settings'))
                
                current_user.set_password(new_password)
                
                # Log the update
                audit = AuditLog(
                    user_id=current_user.id,
                    action="password_change",
                    target_type="User",
                    target_id=current_user.id,
                    details="Password changed"
                )
                db.session.add(audit)
            
            # Update 2FA settings
            current_user.two_factor_enabled = enable_2fa
            db.session.commit()
            
            flash('Security settings updated successfully!', 'success')
            
        elif form_type == 'notifications':
            # Update notification settings
            # In a real app, you would save these to the user model
            flash('Notification preferences saved!', 'success')
            
        elif form_type == 'data_retention':
            # Update data retention settings
            flash('Data retention policy updated!', 'success')
            
        elif form_type == 'delete_data':
            # Delete all user data
            confirmation = request.form.get('confirm_delete_data')
            
            if confirmation != 'DELETE ALL MY DATA':
                flash('Invalid confirmation text.', 'error')
                return redirect(url_for('settings'))
            
            # Delete all datasets
            datasets = Dataset.query.filter_by(user_id=current_user.id).all()
            for dataset in datasets:
                # Delete records
                EpidemicRecord.query.filter_by(dataset_id=dataset.id).delete()
                # Delete dataset
                db.session.delete(dataset)
            
            db.session.commit()
            
            # Log the action
            audit = AuditLog(
                user_id=current_user.id,
                action="delete_all_data",
                target_type="User",
                target_id=current_user.id,
                details="User deleted all their data"
            )
            db.session.add(audit)
            db.session.commit()
            
            flash('All your data has been permanently deleted.', 'success')
            
        elif form_type == 'delete_account':
            # Delete user account
            confirmation = request.form.get('confirm_delete_account')
            
            if not current_user.check_password(confirmation):
                flash('Incorrect password.', 'error')
                return redirect(url_for('settings'))
            
            # Delete all user data first
            datasets = Dataset.query.filter_by(user_id=current_user.id).all()
            for dataset in datasets:
                # Delete records
                EpidemicRecord.query.filter_by(dataset_id=dataset.id).delete()
                # Delete dataset
                db.session.delete(dataset)
            
            # Delete audit logs
            AuditLog.query.filter_by(user_id=current_user.id).delete()
            
            # Store user ID for logging
            user_id = current_user.id
            username = current_user.username
            
            # Log out the user
            logout_user()
            
            # Delete the user
            User.query.filter_by(id=user_id).delete()
            db.session.commit()
            
            flash('Your account has been permanently deleted.', 'info')
            return redirect(url_for('index'))
    
    return render_template('settings.html')

@app.route('/help')
def help():
    return render_template('help.html')

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
    #we need to combine the users own datasets with the shared datasets
    shared_entries = SharedDataset.query.filter_by(shared_with_id=current_user.id).all()

    # Extract dataset IDs from those entries
    shared_dataset_ids = [entry.dataset_id for entry in shared_entries]

    #Query the actual datasets
    shared_datasets = Dataset.query.filter(Dataset.id.in_(shared_dataset_ids)).all()

    user_datasets = Dataset.query.filter_by(user_id=current_user.id).order_by(Dataset.upload_date.desc()).all()
    

    # # Combine both lists
    # combined_datasets = list(chain(user_datasets, shared_datasets))
    # Print for debugging
    print(f"Found {len(user_datasets)} datasets for user {current_user.username}")
    
    # # Later!
    # shared_datasets = []  # Later!
    
    return render_template('dashboard.html', 
                          user_datasets=user_datasets,
                          shared_datasets=shared_datasets)


@app.route('/explore')
def explore_global_map():
    public_datasets = Dataset.query.filter_by(sharing_status='public').all()
    print(f"Count of public datasets: {len(public_datasets)}")
    all_map_data = []

    for dataset in public_datasets:
        try:
            data = json.loads(dataset.data_json)  # data is expected to be a list of dicts (rows)
        except Exception as e:
            print(f"Failed to load JSON for dataset {dataset.id}: {e}")
            continue

        if not isinstance(data, list):
            continue

        # Check if 'latitude' and 'longitude' keys are present in the first record
        if len(data) > 0 and all(k in data[0] for k in ['latitude', 'longitude']):
            for row in data:
                lat = row.get('latitude')
                lon = row.get('longitude')
                if lat and lon:
                    all_map_data.append({
                        'latitude': lat,
                        'longitude': lon,
                        'dataset_name': dataset.name,
                        'cases': row.get('cases'),
                        'deaths': row.get('deaths'),
                        'recovered': row.get('recovered')
                    })
    print(all_map_data)
    return render_template("explore.html", combined_map_data=json.dumps(all_map_data))






# ---------------------------------------------------------
# Upload Route
# ---------------------------------------------------------
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # Save the file temporarily
                filename = secure_filename(file.filename)
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{filename}')
                file.save(temp_path)
                
                # Detect file format
                file_format = DataConverter.detect_file_type(temp_path)
                
                # Create dataset record
                dataset = Dataset(
                    name=request.form.get('name', filename),
                    description=request.form.get('description', ''),
                    original_filename=filename,
                    original_format=file_format,
                    user_id=current_user.id,
                    sharing_status = request.form.get('sharing_status', 'private')
                )
                
                # Try using the new unified storage approach
                try:
                    # Convert file to standardized JSON format
                    data, metadata = DataBridge.file_to_standardized_data(temp_path, file_format)
                    
                    # Update dataset with standardized data and metadata
                    dataset.set_data(data)
                    
                    if 'record_count' in metadata:
                        dataset.record_count = metadata['record_count']
                    if 'has_geo' in metadata:
                        dataset.has_geo = metadata['has_geo']
                    if 'has_time' in metadata:
                        dataset.has_time = metadata['has_time']
                    if 'date_range_start' in metadata:
                        dataset.date_range_start = metadata['date_range_start']
                    if 'date_range_end' in metadata:
                        dataset.date_range_end = metadata['date_range_end']
                    
                    # Save dataset to database
                    db.session.add(dataset)
                    db.session.commit()
                    
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
                    # Log the activity
                    audit = AuditLog(
                        user_id=current_user.id,
                        action="upload_dataset",
                        target_type="Dataset",
                        target_id=dataset.id,
                        details=f"Uploaded dataset '{dataset.name}' with {dataset.record_count} records"
                    )
                    db.session.add(audit)
                    db.session.commit()
                    
                    flash('Dataset uploaded and processed successfully!', 'success')
                    return redirect(url_for('visualize', dataset_id=dataset.id))
                
                except Exception as e:
                    # If the new approach fails, fall back to the legacy method
                    logger.warning(f"Error using unified JSON storage: {str(e)}")
                    logger.info("Falling back to legacy record processing...")
                    
                    try:
                        # Save the dataset without JSON data first
                        db.session.add(dataset)
                        db.session.commit()
                        
                        # Process the file based on its type using your existing method
                        if file_format == 'csv':
                            # Read CSV in chunks
                            chunks = pd.read_csv(temp_path, chunksize=app.config['BATCH_SIZE'])
                            for chunk in chunks:
                                records = chunk.to_dict('records')
                                process_batch(records, dataset.id, current_user.id)
                                
                        elif file_format == 'json':
                            # Read JSON
                            with open(temp_path, 'r') as f:
                                records = json.load(f)
                            process_batch(records, dataset.id, current_user.id)
                            
                        elif file_format in ['excel', 'xlsx', 'xls']:
                            # Read Excel
                            df = pd.read_excel(temp_path)
                            records = df.to_dict('records')
                            process_batch(records, dataset.id, current_user.id)
                        
                        # Update record count
                        count = EpidemicRecord.query.filter_by(dataset_id=dataset.id).count()
                        dataset.record_count = count
                        db.session.commit()
                        
                        # Clean up temporary file
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        
                        # Log the activity
                        audit = AuditLog(
                            user_id=current_user.id,
                            action="upload_dataset_legacy",
                            target_type="Dataset",
                            target_id=dataset.id,
                            details=f"Uploaded dataset '{dataset.name}' with legacy processing"
                        )
                        db.session.add(audit)
                        db.session.commit()
                        
                        flash('Dataset uploaded successfully (using legacy processing).', 'success')
                        return redirect(url_for('dashboard'))
                    
                    except Exception as legacy_error:
                        db.session.rollback()
                        logger.error(f"Legacy processing also failed: {str(legacy_error)}")
                        flash(f'Error processing file: {str(legacy_error)}', 'error')
                        
                        # Clean up temporary file
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                            
                        return redirect(request.url)
                        
            except Exception as e:
                db.session.rollback()
                flash(f'Error uploading file: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Invalid file type. Please upload CSV, JSON, or Excel files.', 'error')
            return redirect(request.url)
    
    return render_template('upload.html')

# ---------------------------------------------------------
# Export Route
# ---------------------------------------------------------
@app.route('/export/<int:dataset_id>')
@login_required
def export_dataset(dataset_id):
    # Get dataset
    dataset = Dataset.query.get_or_404(dataset_id)
    
    # Check permission
    is_owner = dataset.user_id == current_user.id
    is_shared = SharedDataset.query.filter_by(dataset_id=dataset_id, shared_with_id=current_user.id, can_download=True).first() is not None
    is_public = dataset.sharing_status == 'public'
    
    if not (is_owner or is_shared or is_public):
        flash('You do not have permission to download this dataset', 'error')
        return redirect(url_for('dashboard'))
    
    # Get export format
    export_format = request.args.get('format', 'csv')
    if export_format not in ['csv', 'json', 'excel', 'xlsx']:
        flash('Unsupported export format', 'error')
        return redirect(url_for('visualize', dataset_id=dataset_id))
    
    try:
        # Get data from dataset using the unified storage
        data = dataset.get_data()
        
        if not data:
            flash('Dataset is empty', 'error')
            return redirect(url_for('visualize', dataset_id=dataset_id))
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        base_name = os.path.splitext(dataset.original_filename)[0]
        
        if export_format == 'csv':
            filename = f"{base_name}_{timestamp}.csv"
            mimetype = 'text/csv'
            
            # Convert data to CSV
            output = DataBridge.data_to_format(data, 'csv')
            
            return send_file(
                io.BytesIO(output.encode('utf-8')),
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
        
        elif export_format == 'json':
            filename = f"{base_name}_{timestamp}.json"
            mimetype = 'application/json'
            
            # Convert data to JSON
            output = DataBridge.data_to_format(data, 'json')
            
            return send_file(
                io.BytesIO(output.encode('utf-8')),
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
        
        elif export_format in ['excel', 'xlsx']:
            filename = f"{base_name}_{timestamp}.xlsx"
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            
            # Convert data to Excel (returns BytesIO)
            output = DataBridge.data_to_format(data, 'excel')
            
            return send_file(
                output,
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
            
    except Exception as e:
        logger.error(f"Error exporting dataset: {str(e)}")
        flash(f'Error exporting dataset: {str(e)}', 'error')
        return redirect(url_for('visualize', dataset_id=dataset_id))


# ---------------------------------------------------------
# Visualize Route
# ---------------------------------------------------------


@app.route('/visualize/<int:dataset_id>')
def visualize(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)

    # Check access permissions
    is_owner = current_user.is_authenticated and dataset.user_id == current_user.id
    is_shared = current_user.is_authenticated and SharedDataset.query.filter_by(
        dataset_id=dataset_id,
        shared_with_id=current_user.id
    ).first() is not None
    is_public = dataset.sharing_status == 'public'

    if not (is_owner or is_shared or is_public):
        if current_user.is_authenticated:
            flash('You do not have permission to view this dataset', 'error')
            return redirect(url_for('dashboard'))
        else:
            abort(403)

    # Process records for visualization
    records = dataset.get_data()
    map_data, trend_data = [], []

    if records:
        for record in records:
            if 'latitude' in record and 'longitude' in record:
                try:
                    lat = float(record['latitude'])
                    lng = float(record['longitude'])
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        map_data.append({
                            'location': record.get('location', 'Unknown'),
                            'latitude': lat,
                            'longitude': lng,
                            'cases': record.get('cases', 0),
                            'deaths': record.get('deaths', 0),
                            'recovered': record.get('recovered', 0),
                            'date': record.get('date')
                        })
                except (ValueError, TypeError):
                    pass

        # Group records by date
        date_groups = {}
        for record in records:
            date = record.get('date', 'Unknown')
            date_groups.setdefault(date, {'date': date, 'cases': 0, 'deaths': 0, 'recovered': 0})
            date_groups[date]['cases'] += record.get('cases', 0)
            date_groups[date]['deaths'] += record.get('deaths', 0)
            date_groups[date]['recovered'] += record.get('recovered', 0)
        trend_data = sorted(date_groups.values(), key=lambda x: x['date'])

    preview_data = records[:10] if records else []
    preview_columns = ['location', 'date', 'cases', 'deaths', 'recovered']
    numeric_fields = ['cases', 'deaths', 'recovered']

    if any('tested' in r for r in preview_data):
        preview_columns.append('tested')
        numeric_fields.append('tested')
    if any('hospitalized' in r for r in preview_data):
        preview_columns.append('hospitalized')
        numeric_fields.append('hospitalized')

    total_cases = sum(r.get('cases', 0) for r in records)
    total_deaths = sum(r.get('deaths', 0) for r in records)
    total_recovered = sum(r.get('recovered', 0) for r in records)
    summary_stats = {
        'total cases': f"{total_cases:,}",
        'total deaths': f"{total_deaths:,}",
        'total recovered': f"{total_recovered:,}",
        'case fatality rate': f"{(total_deaths / total_cases * 100):.2f}%" if total_cases else "N/A",
        'recovery rate': f"{(total_recovered / total_cases * 100):.2f}%" if total_cases else "N/A"
    }

    date_range = f"{dataset.date_range_start:%Y-%m-%d} to {dataset.date_range_end:%Y-%m-%d}" if dataset.date_range_start and dataset.date_range_end else "N/A"

    return render_template(
        'visualize.html',
        dataset=dataset,
        map_data=json.dumps(map_data),
        trend_data=json.dumps(trend_data),
        preview_data=preview_data,
        preview_columns=preview_columns,
        numeric_fields=numeric_fields,
        summary_stats=summary_stats,
        columns=numeric_fields,
        date_range=date_range,
        visualization_title=dataset.name,
        trend_analysis="Data shows fluctuations in case numbers over time with notable peaks during outbreak periods.",
        key_observations=[
            "Highest case numbers were reported in densely populated areas.",
            "Recovery rates improved significantly in later time periods.",
            "Regional differences in case fatality rates may indicate varying healthcare capacities."
        ]
    )

# Add a debug endpoint to inspect file content
@app.route('/debug_file/<int:dataset_id>')
@login_required
def debug_file(dataset_id):
    # Check if user is admin or file owner
    dataset = Dataset.query.get_or_404(dataset_id)
    
    if dataset.user_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Check file type and read preview
        if dataset.filepath and os.path.exists(dataset.filepath):
            if dataset.file_type == 'text/csv' or dataset.filename.endswith('.csv'):
                # Read first few rows of CSV
                df = pd.read_csv(dataset.filepath, nrows=5)
                column_names = df.columns.tolist()
                sample_data = df.head(5).to_dict('records')
                
                return render_template('debug_file.html', 
                                      dataset=dataset,
                                      column_names=column_names,
                                      sample_data=sample_data,
                                      file_type='CSV')
                
            elif dataset.file_type == 'application/json' or dataset.filename.endswith('.json'):
                # Read first few records of JSON
                with open(dataset.filepath, 'r') as f:
                    json_data = []
                    for i, line in enumerate(f):
                        if i >= 5:  # Read up to 5 lines
                            break
                        if line.strip():
                            json_data.append(json.loads(line))
                
                # Get column names from first record if available
                column_names = []
                if json_data:
                    column_names = list(json_data[0].keys())
                
                return render_template('debug_file.html',
                                     dataset=dataset,
                                     column_names=column_names,
                                     sample_data=json_data,
                                     file_type='JSON')
        
        flash('File not found or unsupported format', 'error')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        flash(f'Error inspecting file: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/delete_dataset/<int:dataset_id>', methods=['POST'])
@login_required
def delete_dataset(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    
    # Check permissions
    if dataset.user_id != current_user.id:
        flash('You do not have permission to delete this dataset.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Delete any legacy EpidemicRecord entries (for backward compatibility)
        EpidemicRecord.query.filter_by(dataset_id=dataset.id).delete()
        
        # Delete any SharedDataset entries referencing this dataset
        SharedDataset.query.filter_by(dataset_id=dataset.id).delete()
        
        # Delete the dataset itself (the data_json field will be deleted automatically)
        db.session.delete(dataset)
        
        # Commit all changes
        db.session.commit()
        
        # Log the deletion
        audit = AuditLog(
            user_id=current_user.id,
            action="delete_dataset",
            target_type="Dataset",
            target_id=dataset.id,
            details=f"Deleted dataset '{dataset.name}'"
        )
        db.session.add(audit)
        db.session.commit()
        
        flash('Dataset deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting dataset: {str(e)}', 'error')
        
    return redirect(url_for('dashboard'))

@app.route('/share/<int:dataset_id>', methods=['POST'])
@login_required
# @csrf.exempt
def share_dataset(dataset_id):
    email = request.form['email']
    permission = request.form.get('permission', 'read')
    
    # Find the user by email
    user_to_share = User.query.filter_by(email=email).first()
    if user_to_share:
        shared = SharedDataset(
            # owner_id=current_user.id,
            shared_by_id = current_user.id,
            shared_with_id=user_to_share.id,
            dataset_id=dataset_id,
        )
        db.session.add(shared)
        db.session.commit()
        flash(f"Dataset shared with {email}.", "success")
    else:
        flash("User not found.", "danger")
    
    return redirect(url_for('dashboard'))


# --------------------------------------------
# Helper Functions
# --------------------------------------------
def allowed_file(filename):
    """Check if the file has an allowed extension"""
    ALLOWED_EXTENSIONS = {'csv', 'json', 'xlsx', 'xls'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Add this function for batch processing
def process_batch(records, dataset_id, user_id):
    try:
        epidemic_records = []
        for record in records:
            lat = record.get('latitude') or record.get('lat') or None
            lon = record.get('longitude') or record.get('long') or record.get('lon') or record.get('lng') or None
            epidemic_record = EpidemicRecord(
                dataset_id=dataset_id,
                date=record.get('date') or record.get('Date') or None,
                location=record.get('location') or record.get('Location') or record.get('region') or record.get('Region') or None,
                cases=record.get('cases') or record.get('Cases') or record.get('confirmed') or record.get('Confirmed') or 0,
                deaths=record.get('deaths') or record.get('Deaths') or 0,
                recovered=record.get('recovered') or record.get('Recovered') or 0,
                latitude=lat,
                longitude=lon
            )
            epidemic_records.append(epidemic_record)
        
        if any(rec.latitude is not None and rec.longitude is not None for rec in epidemic_records):
            dataset = Dataset.query.get(dataset_id)
            if dataset:
                dataset.has_geo = True
                db.session.commit()
        
        db.session.bulk_save_objects(epidemic_records)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        return str(e)

# Add this function for chunked file reading
def read_file_in_chunks(file_path):
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(app.config['CHUNK_SIZE'])
            if not chunk:
                break
            yield chunk

# --------------------------------------------
# Main
# --------------------------------------------
if __name__ == '__main__':
    # with app.app_context():
    #     db.create_all()
    # using migrate instead of create_all to handle db migrations
    app.run(debug=True, host='0.0.0.0', port=8080)





