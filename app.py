from flask import Flask, render_template, redirect, send_file, url_for, flash, request
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from models import db, User, AuditLog
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timezone
from flask_migrate import Migrate
import os
import logging
from flask_mail import Mail

# Initialize the main Flask application
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

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # or your mail server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'harpreetvallah2@gmail.com'
app.config['MAIL_PASSWORD'] = 'owoz huca itgc zvqj'  # Use an app-specific password

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('app')

# folders setup
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)
mail = Mail(app)

# Set up login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Import blueprint modules
from blueprints.auth import auth_bp
from blueprints.main import main_bp
from blueprints.profile import profile_bp
from blueprints.data import data_bp
from blueprints.api import api_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(data_bp)
app.register_blueprint(api_bp, url_prefix='/api')

# Exempt the API blueprint from CSRF protection
csrf.exempt(api_bp)


if __name__ == '__main__':
    # with app.app_context():
    #     db.create_all()
    # using migrate instead of create_all to handle db migrations
    app.run(debug=True, host='0.0.0.0', port=8080)