from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from models import db, User, AuditLog
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
from flask_migrate import Migrate

from models import db, User, AuditLog, PasswordResetToken
import secrets
from forms import EditProfileForm
from werkzeug.utils import secure_filename
import os
import pandas as pd
import numpy as np
import json


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
    # Example placeholder - you can load user's datasets later
    user_datasets = []
    shared_datasets = []
    return render_template('dashboard.html',
                           user_datasets=user_datasets,
                           shared_datasets=shared_datasets)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    # Placeholder upload page
    return render_template('upload.html')

# --------------------------------------------
# Main
# --------------------------------------------
if __name__ == '__main__':
    # with app.app_context():
    #     db.create_all()
    # using migrate instead of create_all to handle db migrations
    app.run(debug=True, host='0.0.0.0', port=8080)





