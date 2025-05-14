from flask import Flask, render_template, redirect, send_file, url_for, flash, request
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from models import db, User, AuditLog
from datetime import datetime, timezone
from models import db, User, AuditLog, PasswordResetToken
import secrets
from flask import abort, flash, redirect, url_for
from twilio.rest import Client
from flask import session
from flask_mail import Mail, Message
import pyotp
from flask_mail import Mail
from flask import current_app

mail = Mail()
from . import auth_bp

# --------------------------------------------
# Routes
# --------------------------------------------
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

            We're excited to have you on board. If you have any questions, feel free to reach out.

            Best regards,  
            The Team
            """
    msg = Message(subject, sender=('Epidemic Monitoring System',"your_email@gmail.com"), recipients=[user_email])
    msg.body = body
    mail.send(msg)

def send_otp(mobile, otp):
    client = Client(current_app.config['TWILIO_ACCOUNT_SID'], current_app.config['TWILIO_AUTH_TOKEN'])
    message = client.messages.create(
        body=f'Your OTP is: {otp}',
        from_=current_app.config['TWILIO_PHONE_NUMBER'],
        to=mobile
    )


@auth_bp.route('/signup', methods=['GET', 'POST'])
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

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        # Get OTP from form
        entered_otp = request.form.get('otp')
        
        # Retrieve user ID from the session
        user_id = session.get('user_id')
        
        if user_id:
            # Fetch user based on the stored user ID
            user = db.session.get(User, user_id)
            
            if user and user.otp == entered_otp:
                login_user(user)
                flash('OTP verified. You are now logged in.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid OTP. Please try again.', 'error')
        else:
            flash('No user ID found in session. Please start the OTP process again.', 'error')

    return render_template('verify_otp.html')



@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember_me' in request.form

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)

            # Update last login time
            user.last_login = datetime.now(timezone.utc)
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
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))



#Forgot Password
@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
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
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc)
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
@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = PasswordResetToken.query.filter_by(token=token).first()

    if not reset_token:
        flash('Invalid or expired token', 'error')
        return redirect(url_for('login'))

    user = db.session.get(User, reset_token.user_id)

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

@auth_bp.route('/reset_success')
def reset_success():
    return render_template('reset_success.html')