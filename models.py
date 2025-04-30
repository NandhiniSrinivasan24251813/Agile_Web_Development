from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
<<<<<<< HEAD
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
=======
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
>>>>>>> 17afde6 (data tables and ERD)

# Initialize SQLAlchemy
db = SQLAlchemy()
<<<<<<< HEAD
# from Nandhini's ERD
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    datasets = db.relationship('Dataset', backref='owner', lazy=True)
    shared_datasets = db.relationship('SharedDataset', backref='shared_user', lazy=True, foreign_keys='SharedDataset.shared_with_id')
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Dataset(db.Model):
    __tablename__ = 'datasets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_type = db.Column(db.String(20))
    record_count = db.Column(db.Integer, default=0)
    date_range_start = db.Column(db.Date)
    date_range_end = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    

    epidemic_records = db.relationship('EpidemicRecord', backref='dataset', lazy=True)
    shared_with = db.relationship('SharedDataset', backref='dataset', lazy=True)

class EpidemicRecord(db.Model):
    __tablename__ = 'epidemic_records'
    
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(100), nullable=False)
=======

# ----------------------------------
# User Model
# ----------------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    datasets = db.relationship('Dataset', backref='owner', cascade="all, delete-orphan", lazy=True)
    shared_with_me = db.relationship('SharedDataset', backref='shared_user', cascade="all, delete-orphan", lazy=True, foreign_keys='SharedDataset.shared_with_id')
    reset_tokens = db.relationship('PasswordResetToken', backref='user', cascade="all, delete-orphan", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# ----------------------------------
# Dataset Model
# ----------------------------------
class Dataset(db.Model):
    __tablename__ = 'datasets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_type = db.Column(db.String(10))
    record_count = db.Column(db.Integer)
    date_range_start = db.Column(db.Date)
    date_range_end = db.Column(db.Date)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    shared_with = db.relationship('SharedDataset', backref='dataset', cascade="all, delete-orphan", lazy=True)
    records = db.relationship('EpidemicRecord', backref='dataset', cascade="all, delete-orphan", lazy=True)

    def __repr__(self):
        return f'<Dataset {self.name}>'

# ----------------------------------
# SharedDataset Model
# ----------------------------------
class SharedDataset(db.Model):
    __tablename__ = 'shared_datasets'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False)
    shared_with_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    share_date = db.Column(db.DateTime, default=datetime.utcnow)
    access_token = db.Column(db.String(64), unique=True, nullable=False)
    can_download = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime)

    __table_args__ = (db.UniqueConstraint('dataset_id', 'shared_with_id', name='uix_dataset_user'),)

    def __repr__(self):
        return f'<SharedDataset {self.dataset_id} -> {self.shared_with_id}>'

# ----------------------------------
# EpidemicRecord Model
# ----------------------------------
class EpidemicRecord(db.Model):
    __tablename__ = 'epidemic_records'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False)

    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(255))
>>>>>>> 17afde6 (data tables and ERD)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    cases = db.Column(db.Integer)
    deaths = db.Column(db.Integer)
    recovered = db.Column(db.Integer)
    hospitalized = db.Column(db.Integer)
    tested = db.Column(db.Integer)
<<<<<<< HEAD
    severity = db.Column(db.String(20))
    postcode = db.Column(db.String(20))
    region = db.Column(db.String(100))
    country = db.Column(db.String(100))


class SharedDataset(db.Model):
    __tablename__ = 'shared_datasets'
    
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False)
    shared_with_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    share_date = db.Column(db.DateTime)
    access_token = db.Column(db.String(255))
    can_download = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime)


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255))
    created_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)



class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  
    target_type = db.Column(db.String(50))              
    target_id = db.Column(db.Integer)                   
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text)  

    def __repr__(self):
        return f'<AuditLog {self.action} by User {self.user_id} at {self.timestamp}>'
=======
    severity = db.Column(db.String(64))
    postcode = db.Column(db.String(20))
    region = db.Column(db.String(128))
    country = db.Column(db.String(128))

    __table_args__ = (
        db.Index('ix_date_location', 'date', 'location'),
    )

    def __repr__(self):
        return f'<Record {self.date} - {self.location}>'

# ----------------------------------
# PasswordResetToken Model
# ----------------------------------
class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=1))

    def __repr__(self):
        return f'<ResetToken user={self.user_id}>'
>>>>>>> 17afde6 (data tables and ERD)
