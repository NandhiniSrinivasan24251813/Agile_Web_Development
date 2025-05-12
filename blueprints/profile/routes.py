# blueprints/profile/routes.py
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user, logout_user
from models import db, User, AuditLog, Dataset, EpidemicRecord
from forms import EditProfileForm
from werkzeug.utils import secure_filename
from . import profile_bp
import os
from datetime import datetime, timezone


@profile_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


@profile_bp.route('/settings', methods=['GET', 'POST'])
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
                return redirect(url_for('profile.settings'))
            
            # Update password if provided
            if new_password:
                if new_password != confirm_password:
                    flash('New passwords do not match.', 'error')
                    return redirect(url_for('profile.settings'))
                
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
                return redirect(url_for('profile.settings'))
            
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
                return redirect(url_for('profile.settings'))
            
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
            return redirect(url_for('main.index'))
    
    return render_template('settings.html')

@profile_bp.route('/edit_profile', methods=['GET', 'POST'])
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
        current_user.last_seen = datetime.now(timezone.utc)

        if form.profile_picture.data:
            picture_file = secure_filename(form.profile_picture.data.filename)
            picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_file)
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            form.profile_picture.data.save(picture_path)
            current_user.profile_picture = picture_file

        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('profile.profile'))

    return render_template('edit_profile.html', form=form)