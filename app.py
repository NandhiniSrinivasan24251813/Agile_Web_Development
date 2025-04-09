from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    abort,
    session,
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import os
import json
import csv
import pandas as pd
from datetime import datetime
import uuid
import sqlite3
import secrets

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(16)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///epidemic.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload size

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize database
db = SQLAlchemy(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    datasets = db.relationship("Dataset", backref="owner", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    shared_with = db.relationship("SharedDataset", backref="dataset", lazy=True)


class SharedDataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("dataset.id"), nullable=False)
    shared_with_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    share_date = db.Column(db.DateTime, default=datetime.utcnow)
    access_token = db.Column(db.String(64), nullable=False, unique=True)

    # Define a relationship to get the user this dataset is shared with
    shared_user = db.relationship("User", foreign_keys=[shared_with_id])


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))
        else:
            flash("Invalid username or password")

    return render_template("auth/login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return render_template("auth/signup.html")

        if User.query.filter_by(email=email).first():
            flash("Email already exists")
            return render_template("auth/signup.html")

        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Account created successfully! Please log in.")
        return redirect(url_for("login"))

    return render_template("auth/signup.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    datasets = Dataset.query.filter_by(user_id=current_user.id).all()
    shared_datasets = SharedDataset.query.filter_by(
        shared_with_id=current_user.id
    ).all()
    return render_template(
        "dashboard.html", datasets=datasets, shared_datasets=shared_datasets
    )


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        # Check if the post request has the file part
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)

        file = request.files["file"]

        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)

        if file:
            # Generate unique filename
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)

            # Save file
            file.save(filepath)

            # Create dataset record
            dataset = Dataset(
                name=request.form.get("name"),
                description=request.form.get("description"),
                filename=unique_filename,
                user_id=current_user.id,
            )

            db.session.add(dataset)
            db.session.commit()

            flash("File uploaded successfully")
            return redirect(url_for("dashboard"))

    return render_template("upload.html")


@app.route("/visualize/<int:dataset_id>")
@login_required
def visualize(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)

    # Check if user has access to this dataset
    if (
        dataset.user_id != current_user.id
        and not SharedDataset.query.filter_by(
            dataset_id=dataset_id, shared_with_id=current_user.id
        ).first()
    ):
        abort(403)

    return render_template("visualize.html", dataset=dataset)


@app.route("/api/dataset/<int:dataset_id>")
@login_required
def get_dataset(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)

    # Check if user has access to this dataset
    if (
        dataset.user_id != current_user.id
        and not SharedDataset.query.filter_by(
            dataset_id=dataset_id, shared_with_id=current_user.id
        ).first()
    ):
        abort(403)

    # Read dataset file
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], dataset.filename)

    data = []
    if dataset.filename.endswith(".csv"):
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    elif dataset.filename.endswith(".json"):
        with open(filepath, "r") as f:
            data = json.load(f)

    return jsonify(data)


@app.route("/share/<int:dataset_id>", methods=["GET", "POST"])
@login_required
def share(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)

    # Check if user owns this dataset
    if dataset.user_id != current_user.id:
        abort(403)

    if request.method == "POST":
        username = request.form.get("username")
        user_to_share_with = User.query.filter_by(username=username).first()

        if not user_to_share_with:
            flash("User not found")
            return redirect(url_for("share", dataset_id=dataset_id))

        # Check if already shared
        if SharedDataset.query.filter_by(
            dataset_id=dataset_id, shared_with_id=user_to_share_with.id
        ).first():
            flash("Already shared with this user")
            return redirect(url_for("share", dataset_id=dataset_id))

        # Create share record
        shared_dataset = SharedDataset(
            dataset_id=dataset_id,
            shared_with_id=user_to_share_with.id,
            access_token=secrets.token_urlsafe(32),
        )

        db.session.add(shared_dataset)
        db.session.commit()

        flash(f"Dataset shared with {username}")
        return redirect(url_for("share", dataset_id=dataset_id))

    shared_users = SharedDataset.query.filter_by(dataset_id=dataset_id).all()
    return render_template("share.html", dataset=dataset, shared_users=shared_users)


@app.route("/revoke-share/<int:share_id>")
@login_required
def revoke_share(share_id):
    shared_dataset = SharedDataset.query.get_or_404(share_id)
    dataset = Dataset.query.get(shared_dataset.dataset_id)

    # Check if user owns this dataset
    if dataset.user_id != current_user.id:
        abort(403)

    db.session.delete(shared_dataset)
    db.session.commit()

    flash("Sharing revoked")
    return redirect(url_for("share", dataset_id=dataset.id))


@app.route("/share-link/<token>")
def share_link(token):
    shared_dataset = SharedDataset.query.filter_by(access_token=token).first_or_404()
    dataset = Dataset.query.get(shared_dataset.dataset_id)

    return render_template("view_shared.html", dataset=dataset)


@app.route("/api/validate-csv", methods=["POST"])
@login_required
def validate_csv():
    if "file" not in request.files:
        return jsonify({"valid": False, "message": "No file provided"})

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"valid": False, "message": "No file selected"})

    if not file.filename.endswith(".csv"):
        return jsonify({"valid": False, "message": "File must be a CSV"})

    try:
        # Read CSV
        df = pd.read_csv(file)

        # Check required columns
        required_columns = ["location", "latitude", "longitude", "date", "cases"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return jsonify(
                {
                    "valid": False,
                    "message": f"Missing required columns: {', '.join(missing_columns)}",
                }
            )

        # Return preview data
        preview = df.head(5).to_dict("records")
        return jsonify(
            {
                "valid": True,
                "message": "CSV is valid",
                "preview": preview,
                "columns": list(df.columns),
            }
        )

    except Exception as e:
        return jsonify({"valid": False, "message": f"Error processing CSV: {str(e)}"})


# Create the database tables
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
