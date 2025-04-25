from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, current_user, login_required
from models import db, User
from flask_wtf.csrf import CSRFProtect

# Initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///epidemic.db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

# placeholders
@app.route('/login', methods=['GET', 'POST'])
def login():

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    return render_template('signup.html')

@app.route('/logout')
def logout():
    flash('Logout functionality will be implemented soon', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    return "Dashboard page will be implemented soon"

@app.route('/upload')
def upload():
    return "Upload page will be implemented soon"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)