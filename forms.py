from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SubmitField, FileField
from wtforms.validators import Length, Optional, Email

class EditProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[Length(max=120)])
    email = StringField('Email', validators=[Email(), Length(max=120)], render_kw={'readonly': True})
    dob = DateField('Date of Birth', format='%Y-%m-%d', validators=[Optional()])
    work_location = StringField('Work Location', validators=[Length(max=100)])
    mobile = StringField('Mobile Number', validators=[Length(max=20)])
    address = StringField('Address', validators=[Length(max=255)])
    city = StringField('City', validators=[Length(max=100)])
    postcode = StringField('Postcode', validators=[Length(max=20)])
    bio = TextAreaField('Bio', validators=[Length(max=500)])
    profile_picture = FileField('Profile Picture')
    submit = SubmitField('Save Changes')
