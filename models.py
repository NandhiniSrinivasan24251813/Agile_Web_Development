from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


# From Nandhini's ERD
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    datasets = db.relationship('Dataset', backref='user', lazy=True)
    shared_access = db.relationship('SharedDataset', backref='shared_user',
                                    foreign_keys='SharedDataset.shared_with_id', lazy=True)
    reset_tokens = db.relationship('PasswordResetToken', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


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

    # Relationships
    records = db.relationship('EpidemicRecord', backref='dataset', lazy=True,
                              cascade='all, delete-orphan')
    shares = db.relationship('SharedDataset', backref='dataset', lazy=True,
                             cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Dataset {self.name}>'


class EpidemicRecord(db.Model):
    __tablename__ = 'epidemic_records'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    cases = db.Column(db.Integer)
    deaths = db.Column(db.Integer)
    recovered = db.Column(db.Integer)
    hospitalized = db.Column(db.Integer)
    tested = db.Column(db.Integer)
    severity = db.Column(db.String(20))
    postcode = db.Column(db.String(20))
    region = db.Column(db.String(100))
    country = db.Column(db.String(100))

    def __repr__(self):
        return f'<EpidemicRecord {self.location} on {self.date}>'


class SharedDataset(db.Model):
    __tablename__ = 'shared_datasets'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False)
    shared_with_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    share_date = db.Column(db.DateTime, default=datetime.utcnow)
    access_token = db.Column(db.String(255))
    can_download = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<SharedDataset {self.dataset_id} shared with {self.shared_with_id}>'


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<PasswordResetToken for user {self.user_id}>'