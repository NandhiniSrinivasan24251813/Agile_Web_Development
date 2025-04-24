from flask import Flask, render_template, flash, redirect, url_for, request, jsonify, abort
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Dataset, EpidemicRecord, SharedDataset, PasswordResetToken
from datetime import datetime, timedelta
import os
import uuid
import json
import csv
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///epidemic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
db.init_app(app)

# Create uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Routes
@app.route("/")
def index():
    return render_template("home.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template("auth/login.html")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()

            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            # Make sure the next page is on our site to prevent open redirect
            if next_page and not next_page.startswith('/'):
                next_page = None
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template("auth/login.html")


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template("auth/signup.html")

        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template("auth/signup.html")

        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template("auth/signup.html")

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template("auth/signup.html")

        # Create new user
        try:
            user = User(username=username, email=email)
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash('Account created successfully! You can now login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            flash('An error occurred. Please try again.', 'error')

    return render_template("auth/signup.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))


@app.route("/dashboard")
@login_required
def dashboard():
    try:
        # Get user's datasets
        datasets = Dataset.query.filter_by(user_id=current_user.id).all()

        # Get datasets shared with the user with owner information
        shared_datasets = SharedDataset.query.filter_by(shared_with_id=current_user.id).all()

        return render_template("dashboard.html", datasets=datasets, shared_datasets=shared_datasets)
    except Exception as e:
        logger.error(f"Error in dashboard: {str(e)}")
        flash('An error occurred while loading the dashboard.', 'error')
        return redirect(url_for('index'))


@app.route("/upload", methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        file = request.files.get('file')

        if not name or not file:
            flash('Dataset name and file are required', 'error')
            return render_template("upload.html")

        # Validate file type
        if not (file.filename.endswith('.csv') or file.filename.endswith('.json')):
            flash('Only CSV and JSON files are supported', 'error')
            return render_template("upload.html")

        try:
            # Save the file
            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Create dataset record
            dataset = Dataset(
                name=name,
                description=description,
                filename=filename,
                file_type=file.filename.split('.')[-1].lower(),
                user_id=current_user.id
            )

            # Process the file to extract records
            record_count = 0
            min_date = None
            max_date = None

            if file.filename.endswith('.csv'):
                with open(file_path, 'r') as f:
                    reader = csv.DictReader(f)
                    df = pd.DataFrame(list(reader))
                    record_count = len(df)

                    # Extract date range if 'date' column exists
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'], errors='coerce')
                        if not df['date'].isnull().all():
                            min_date = df['date'].min().date() if not pd.isnull(df['date'].min()) else None
                            max_date = df['date'].max().date() if not pd.isnull(df['date'].max()) else None

            elif file.filename.endswith('.json'):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        record_count = len(data)

                        # Extract date range if 'date' key exists in records
                        dates = [record.get('date') for record in data if 'date' in record]
                        if dates:
                            dates = pd.to_datetime(dates, errors='coerce')
                            valid_dates = dates[~pd.isnull(dates)]
                            if len(valid_dates) > 0:
                                min_date = min(valid_dates).date()
                                max_date = max(valid_dates).date()

            # Update dataset with extracted info
            dataset.record_count = record_count
            dataset.date_range_start = min_date
            dataset.date_range_end = max_date

            db.session.add(dataset)
            db.session.commit()

            flash('Dataset uploaded successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            try:
                # Clean up the file if it was saved
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass

            logger.error(f"Error uploading file: {str(e)}")
            flash(f'Error processing file: {str(e)}', 'error')

    return render_template("upload.html")


@app.route("/visualize/<int:dataset_id>")
@login_required
def visualize(dataset_id):
    try:
        # Get the dataset
        dataset = Dataset.query.get_or_404(dataset_id)

        # Check if user owns the dataset or it's shared with them
        is_owner = dataset.user_id == current_user.id
        is_shared = SharedDataset.query.filter_by(
            dataset_id=dataset_id,
            shared_with_id=current_user.id
        ).first() is not None

        if not (is_owner or is_shared):
            flash('You do not have permission to view this dataset', 'error')
            return redirect(url_for('dashboard'))

        return render_template("visualize.html", dataset=dataset)
    except Exception as e:
        logger.error(f"Error in visualize: {str(e)}")
        flash('Error loading visualization. The dataset might be invalid.', 'error')
        return redirect(url_for('dashboard'))


@app.route("/share/<int:dataset_id>", methods=['GET', 'POST'])
@login_required
def share(dataset_id):
    try:
        # Get the dataset
        dataset = Dataset.query.get_or_404(dataset_id)

        # Check if user owns the dataset
        if dataset.user_id != current_user.id:
            flash('You do not have permission to share this dataset', 'error')
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            username = request.form.get('username')

            if not username:
                flash('Username is required', 'error')
                return redirect(url_for('share', dataset_id=dataset_id))

            # Find the user to share with
            user = User.query.filter_by(username=username).first()

            if not user:
                flash(f'User {username} not found', 'error')
                return redirect(url_for('share', dataset_id=dataset_id))

            # Don't share with yourself
            if user.id == current_user.id:
                flash('You cannot share a dataset with yourself', 'error')
                return redirect(url_for('share', dataset_id=dataset_id))

            # Check if already shared
            existing_share = SharedDataset.query.filter_by(
                dataset_id=dataset_id,
                shared_with_id=user.id
            ).first()

            if existing_share:
                flash(f'Dataset already shared with {username}', 'warning')
                return redirect(url_for('share', dataset_id=dataset_id))

            # Create shared dataset record
            shared = SharedDataset(
                dataset_id=dataset_id,
                shared_with_id=user.id,
                share_date=datetime.utcnow(),
                access_token=str(uuid.uuid4()),
                can_download=True,
                expires_at=datetime.utcnow() + timedelta(days=30)  # 30-day expiration
            )

            db.session.add(shared)
            db.session.commit()

            flash(f'Dataset shared with {username} successfully!', 'success')
            return redirect(url_for('share', dataset_id=dataset_id))

        # Get users this dataset is shared with
        shared_users = SharedDataset.query.filter_by(dataset_id=dataset_id).all()

        return render_template("share.html", dataset=dataset, shared_users=shared_users)
    except Exception as e:
        logger.error(f"Error in share: {str(e)}")
        flash('An error occurred while processing your request.', 'error')
        return redirect(url_for('dashboard'))


@app.route("/revoke_share/<int:share_id>")
@login_required
def revoke_share(share_id):
    try:
        # Get the shared dataset record
        shared = SharedDataset.query.get_or_404(share_id)

        # Get the dataset
        dataset = Dataset.query.get_or_404(shared.dataset_id)

        # Check if user owns the dataset
        if dataset.user_id != current_user.id:
            flash('You do not have permission to revoke access to this dataset', 'error')
            return redirect(url_for('dashboard'))

        # Delete the shared record
        db.session.delete(shared)
        db.session.commit()

        flash('Dataset access revoked successfully', 'success')
        return redirect(url_for('share', dataset_id=dataset.id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in revoke_share: {str(e)}")
        flash('An error occurred while revoking access.', 'error')
        return redirect(url_for('dashboard'))


@app.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            bio = request.form.get('bio')

            if not username or not email:
                flash('Username and email are required', 'error')
                return redirect(url_for('profile'))

            # Check if username already exists (for another user)
            existing_user = User.query.filter(User.username == username, User.id != current_user.id).first()
            if existing_user:
                flash('Username already exists', 'error')
                return redirect(url_for('profile'))

            # Check if email already exists (for another user)
            existing_email = User.query.filter(User.email == email, User.id != current_user.id).first()
            if existing_email:
                flash('Email already registered', 'error')
                return redirect(url_for('profile'))

            # Update user profile
            current_user.username = username
            current_user.email = email
            if bio:
                current_user.bio = bio

            db.session.commit()
            flash('Profile updated successfully', 'success')
            return redirect(url_for('profile'))

        # Get user's datasets and sharing info for statistics
        datasets = Dataset.query.filter_by(user_id=current_user.id).all()
        shared_with = SharedDataset.query.join(Dataset).filter(Dataset.user_id == current_user.id).all()
        shared_to_me = SharedDataset.query.filter_by(shared_with_id=current_user.id).all()

        return render_template("profile.html", datasets=datasets, shared_with=shared_with, shared_to_me=shared_to_me)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in profile: {str(e)}")
        flash('An error occurred while updating your profile.', 'error')
        return redirect(url_for('dashboard'))


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


# Settings form handlers
@app.route("/settings/account", methods=['POST'])
@login_required
def settings_account():
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            timezone = request.form.get('timezone')

            if not username or not email:
                flash('Username and email are required', 'error')
                return redirect(url_for('settings'))

            # Check if username already exists (for another user)
            existing_user = User.query.filter(User.username == username, User.id != current_user.id).first()
            if existing_user:
                flash('Username already exists', 'error')
                return redirect(url_for('settings'))

            # Check if email already exists (for another user)
            existing_email = User.query.filter(User.email == email, User.id != current_user.id).first()
            if existing_email:
                flash('Email already registered', 'error')
                return redirect(url_for('settings'))

            # Update user account settings
            current_user.username = username
            current_user.email = email
            # Store timezone if your User model has this field

            db.session.commit()
            flash('Account settings updated successfully', 'success')
        return redirect(url_for('settings'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in settings_account: {str(e)}")
        flash('An error occurred while updating your settings.', 'error')
        return redirect(url_for('settings'))


@app.route("/settings/password", methods=['POST'])
@login_required
def settings_password():
    try:
        if request.method == 'POST':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not current_password or not new_password or not confirm_password:
                flash('All password fields are required', 'error')
                return redirect(url_for('settings'))

            # Verify current password
            if not current_user.check_password(current_password):
                flash('Current password is incorrect', 'error')
                return redirect(url_for('settings'))

            # Check if new passwords match
            if new_password != confirm_password:
                flash('New passwords do not match', 'error')
                return redirect(url_for('settings'))

            # Check new password length
            if len(new_password) < 8:
                flash('New password must be at least 8 characters long', 'error')
                return redirect(url_for('settings'))

            # Update password
            current_user.set_password(new_password)
            db.session.commit()

            flash('Password updated successfully', 'success')
        return redirect(url_for('settings'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in settings_password: {str(e)}")
        flash('An error occurred while updating your password.', 'error')
        return redirect(url_for('settings'))


@app.route("/settings/notifications", methods=['POST'])
@login_required
def settings_notifications():
    try:
        if request.method == 'POST':
            # Get notification preferences
            email_notifications = 'email_notifications' in request.form
            shared_dataset_notifications = 'shared_dataset_notifications' in request.form
            data_update_notifications = 'data_update_notifications' in request.form

            # Store preferences if your User model has these fields
            # current_user.email_notifications = email_notifications
            # current_user.shared_dataset_notifications = shared_dataset_notifications
            # current_user.data_update_notifications = data_update_notifications

            # db.session.commit()
            flash('Notification preferences updated successfully', 'success')
        return redirect(url_for('settings'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in settings_notifications: {str(e)}")
        flash('An error occurred while updating notification settings.', 'error')
        return redirect(url_for('settings'))


@app.route("/settings/data_preferences", methods=['POST'])
@login_required
def settings_data_preferences():
    try:
        if request.method == 'POST':
            # Get data display preferences
            default_chart_type = request.form.get('default_chart_type')
            default_map_view = request.form.get('default_map_view')
            date_format = request.form.get('date_format')

            # Store preferences if your User model has these fields
            # current_user.default_chart_type = default_chart_type
            # current_user.default_map_view = default_map_view
            # current_user.date_format = date_format

            # db.session.commit()
            flash('Data display preferences updated successfully', 'success')
        return redirect(url_for('settings'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in settings_data_preferences: {str(e)}")
        flash('An error occurred while updating data preferences.', 'error')
        return redirect(url_for('settings'))


@app.route("/delete_all_datasets", methods=['POST'])
@login_required
def delete_all_datasets():
    try:
        if request.method == 'POST':
            confirmation = request.form.get('confirmation')

            if confirmation != 'DELETE':
                flash('Confirmation text does not match', 'error')
                return redirect(url_for('settings'))

            # Get all user's datasets
            datasets = Dataset.query.filter_by(user_id=current_user.id).all()

            # Delete datasets and associated records
            for dataset in datasets:
                # Remove the file
                try:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], dataset.filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.error(f"Error removing file: {str(e)}")
                    flash(f'Error removing file: {str(e)}', 'error')

                # The cascade delete will handle associated records
                db.session.delete(dataset)

            db.session.commit()

            flash('All datasets deleted successfully', 'success')
        return redirect(url_for('settings'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in delete_all_datasets: {str(e)}")
        flash('An error occurred while deleting datasets.', 'error')
        return redirect(url_for('settings'))


@app.route("/delete_account", methods=['POST'])
@login_required
def delete_account():
    try:
        if request.method == 'POST':
            password = request.form.get('password')

            if not password:
                flash('Password is required to confirm account deletion', 'error')
                return redirect(url_for('settings'))

            # Verify password
            if not current_user.check_password(password):
                flash('Password is incorrect', 'error')
                return redirect(url_for('settings'))

            # Delete all user's datasets
            datasets = Dataset.query.filter_by(user_id=current_user.id).all()

            for dataset in datasets:
                # Remove the file
                try:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], dataset.filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.error(f"Error removing file: {str(e)}")

                # The cascade delete will handle associated records
                db.session.delete(dataset)

            # Delete the user
            user_id = current_user.id
            logout_user()  # Log out before deleting

            user = User.query.get(user_id)
            db.session.delete(user)
            db.session.commit()

            flash('Your account has been deleted successfully', 'success')
            return redirect(url_for('index'))

        return redirect(url_for('settings'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in delete_account: {str(e)}")
        flash('An error occurred while deleting your account.', 'error')
        return redirect(url_for('settings'))


# API Endpoints for AJAX requests
@app.route("/api/dataset/<int:dataset_id>/records")
@login_required
def get_dataset_records(dataset_id):
    try:
        # Get the dataset
        dataset = Dataset.query.get_or_404(dataset_id)

        # Check permissions
        is_owner = dataset.user_id == current_user.id
        is_shared = SharedDataset.query.filter_by(
            dataset_id=dataset_id,
            shared_with_id=current_user.id
        ).first() is not None

        if not (is_owner or is_shared):
            return jsonify({'error': 'Permission denied'}), 403

        # Read the file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], dataset.filename)

        if dataset.file_type == 'csv':
            df = pd.read_csv(file_path)
            data = df.to_dict(orient='records')
        elif dataset.file_type == 'json':
            with open(file_path, 'r') as f:
                data = json.load(f)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400

        return jsonify(data)
    except Exception as e:
        logger.error(f"Error in get_dataset_records: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/validate-csv", methods=['POST'])
@login_required
def validate_csv():
    try:
        if 'file' not in request.files:
            return jsonify({'valid': False, 'message': 'No file provided'}), 400

        file = request.files['file']

        if not file.filename.endswith('.csv'):
            return jsonify({'valid': False, 'message': 'File must be CSV format'}), 400

        # Save the file temporarily
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{secure_filename(file.filename)}")
        file.save(temp_path)

        try:
            # Validate the CSV
            required_fields = ['location', 'latitude', 'longitude', 'date', 'cases']

            with open(temp_path, 'r') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames

                # Check if required fields exist
                missing_fields = [field for field in required_fields if field not in headers]
                if missing_fields:
                    return jsonify({
                        'valid': False,
                        'message': f'Missing required fields: {", ".join(missing_fields)}'
                    }), 400

                # Read sample data for preview
                sample_data = []
                for i, row in enumerate(reader):
                    if i < 5:  # Just get first 5 rows for preview
                        sample_data.append(row)
                    else:
                        break

            # Return success with preview data
            return jsonify({
                'valid': True,
                'message': 'CSV is valid and contains all required fields.',
                'columns': headers,
                'preview': sample_data
            })
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    except Exception as e:
        logger.error(f"Error validating CSV: {str(e)}")
        return jsonify({'valid': False, 'message': f'Error validating file: {str(e)}'}), 500


@app.route("/api/generate-share-link/<int:dataset_id>", methods=['POST'])
@login_required
def generate_share_link(dataset_id):
    try:
        # Get the dataset
        dataset = Dataset.query.get_or_404(dataset_id)

        # Check if user owns the dataset
        if dataset.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Permission denied'}), 403

        # Generate new token
        access_token = str(uuid.uuid4())

        # Create or update shared link
        shared = SharedDataset.query.filter_by(
            dataset_id=dataset_id,
            shared_with_id=None  # Public share has no specific user
        ).first()

        if shared:
            shared.access_token = access_token
            shared.expires_at = datetime.utcnow() + timedelta(days=30)
        else:
            shared = SharedDataset(
                dataset_id=dataset_id,
                shared_with_id=None,  # Public share
                share_date=datetime.utcnow(),
                access_token=access_token,
                can_download=True,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(shared)

        db.session.commit()

        # Generate full URL for share link
        share_link = url_for('view_shared', token=access_token, _external=True)

        return jsonify({'success': True, 'link': share_link})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating share link: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/shared/<token>")
def view_shared(token):
    try:
        # Find the shared dataset by token
        shared = SharedDataset.query.filter_by(access_token=token).first_or_404()

        # Check if share has expired
        if shared.expires_at and shared.expires_at < datetime.utcnow():
            return render_template('404.html', message="This share link has expired."), 404

        # Get the dataset
        dataset = Dataset.query.get_or_404(shared.dataset_id)

        # Add owner information
        dataset.owner = User.query.get(dataset.user_id)

        return render_template("view_shared.html", dataset=dataset)
    except Exception as e:
        logger.error(f"Error viewing shared dataset: {str(e)}")
        return render_template('500.html', error=str(e)), 500


# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    try:
        return render_template('404.html'), 404
    except:
        return '<h1>Page Not Found</h1><p>The requested page does not exist.</p>', 404

@app.errorhandler(500)
def internal_server_error(e):
    try:
        return render_template('500.html'), 500
    except:
        return '<h1>Internal Server Error</h1><p>Something went wrong on our end.</p>', 500

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {str(e)}")
    try:
        return render_template('500.html', error=str(e)), 500
    except:
        return '<h1>Internal Server Error</h1><p>Something went wrong on our end.</p>', 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)