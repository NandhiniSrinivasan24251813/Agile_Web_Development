from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
from utils import DataConverter, JSONEncoder  # from utils.py

db = SQLAlchemy()
# fron Nandihini's ERD
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(80), unique=True, nullable=False)
    email           = db.Column(db.String(120), unique=True, nullable=False)
    password_hash   = db.Column(db.String(255), nullable=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime)
    full_name       = db.Column(db.String(120))
    bio             = db.Column(db.Text)
    work_location   = db.Column(db.String(100)) 
    address         = db.Column(db.String(255))
    postcode        = db.Column(db.String(20))
    city            = db.Column(db.String(100))
    mobile          = db.Column(db.String(20))
    dob             = db.Column(db.Date)
    profile_picture = db.Column(db.String(255))
    timezone        = db.Column(db.String(50), default='UTC')
    two_factor_enabled = db.Column(db.Boolean, default=False)
    otp             = db.Column(db.String(6), nullable=True)
    
    # Relationships
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
    original_filename = db.Column(db.String(255), nullable=False)
    original_format = db.Column(db.String(20))  # Original file format (csv, json, xlsx)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    record_count = db.Column(db.Integer, default=0)
    date_range_start = db.Column(db.Date)
    date_range_end = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Unified data storage as JSON
    data_json = db.Column(db.Text)  # Stores the actual data in JSON format
    
    # Metadata flags
    has_geo = db.Column(db.Boolean, default=False)  
    has_time = db.Column(db.Boolean, default=False)  
    sharing_status = db.Column(db.String(20), default='private')

    # Keep the original relationships for backward compatibility during migration
    epidemic_records = db.relationship('EpidemicRecord', backref='dataset', lazy=True, cascade="all, delete-orphan")
    shared_with = db.relationship('SharedDataset', backref='dataset', lazy=True, cascade="all, delete-orphan")
    
    def get_data(self):
        """Return data as a Python object from stored JSON"""
        if self.data_json:
            return json.loads(self.data_json)
        
        # Fallback to loading from epidemic_records if data_json is empty
        # This enables backward compatibility during migration
        if hasattr(self, 'epidemic_records'):
            records = []
            for record in self.epidemic_records:
                r = {
                    'date': record.date.isoformat() if record.date else None,
                    'location': record.location,
                    'cases': record.cases,
                    'deaths': record.deaths,
                    'recovered': record.recovered
                }
                
                # Add geographic coordinates if available
                if record.latitude and record.longitude:
                    r['latitude'] = record.latitude
                    r['longitude'] = record.longitude
                
                # Add additional fields if they exist
                for field in ['hospitalized', 'tested', 'severity', 'postcode', 'region', 'country']:
                    if hasattr(record, field) and getattr(record, field):
                        r[field] = getattr(record, field)
                
                records.append(r)
            return records
        return []
    
    def set_data(self, data):
        """Set data by converting Python object to JSON"""
        if not data:
            self.data_json = json.dumps([])
            self.record_count = 0
            return
            
        self.data_json = json.dumps(data, cls=JSONEncoder)
        self.record_count = len(data) if isinstance(data, list) else 0
        
        # Update metadata based on the data
        self._update_metadata(data)
    
    def _update_metadata(self, data):
        """Extract and update metadata from the data"""
        if not data or not isinstance(data, list):
            return
            
        # Check for geographic data
        self.has_geo = any(
            'latitude' in record and 'longitude' in record and 
            record['latitude'] is not None and record['longitude'] is not None
            for record in data
        )
        
        # Check for time data and date range
        dates = []
        for record in data:
            if 'date' in record and record['date']:
                try:
                    # Parse the date (could be a string or already a date object)
                    if isinstance(record['date'], str):
                        date_obj = datetime.strptime(record['date'], '%Y-%m-%d').date()
                    else:
                        date_obj = record['date']
                    dates.append(date_obj)
                except (ValueError, TypeError):
                    pass
        
        self.has_time = len(dates) > 0
        
        if dates:
            self.date_range_start = min(dates)
            self.date_range_end = max(dates)


class EpidemicRecord(db.Model):
    """Legacy model for backward compatibility during migration"""
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


class SharedDataset(db.Model):
    __tablename__ = 'shared_datasets'
    
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False)
    shared_with_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    share_date = db.Column(db.DateTime, default=datetime.utcnow)
    access_token = db.Column(db.String(255))
    can_download = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime)


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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