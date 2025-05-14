# blueprints/main/routes.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Dataset, SharedDataset
from . import main_bp
import json
from itertools import chain

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Quickfix 02/05/2025: Get datasets for the current user
    #we need to combine the users own datasets with the shared datasets
    shared_entries = SharedDataset.query.filter_by(shared_with_id=current_user.id).all()

    # Extract dataset IDs from those entries
    shared_dataset_ids = [entry.dataset_id for entry in shared_entries]

    #Query the actual datasets
    shared_datasets = Dataset.query.filter(Dataset.id.in_(shared_dataset_ids)).all()

    user_datasets = Dataset.query.filter_by(user_id=current_user.id).order_by(Dataset.upload_date.desc()).all()
    
    all_users = User.query.all()  ## All users
    return render_template(
        'dashboard.html',
        user_datasets=user_datasets,
        shared_datasets=shared_datasets,
        all_users=all_users
    )
    # # Combine both lists
    # combined_datasets = list(chain(user_datasets, shared_datasets))
    # Print for debugging
    print(f"Found {len(user_datasets)} datasets for user {current_user.username}")
    
    # # Later!
    # shared_datasets = []  # Later!
    
    return render_template('dashboard.html', 
                          user_datasets=user_datasets,
                          shared_datasets=shared_datasets)

@main_bp.route('/explore')
def explore_global_map():
    public_datasets = Dataset.query.filter_by(sharing_status='public').all()
    print(f"Count of public datasets: {len(public_datasets)}")
    all_map_data = []

    for dataset in public_datasets:
        try:
            data = json.loads(dataset.data_json)  # data is expected to be a list of dicts (rows)
        except Exception as e:
            print(f"Failed to load JSON for dataset {dataset.id}: {e}")
            continue

        if not isinstance(data, list):
            continue

        # Check if 'latitude' and 'longitude' keys are present in the first record
        if len(data) > 0 and all(k in data[0] for k in ['latitude', 'longitude']):
            for row in data:
                lat = row.get('latitude')
                lon = row.get('longitude')
                if lat and lon:
                    all_map_data.append({
                        'latitude': lat,
                        'longitude': lon,
                        'dataset_name': dataset.name,
                        'cases': row.get('cases'),
                        'deaths': row.get('deaths'),
                        'recovered': row.get('recovered')
                    })
    print(all_map_data)
    return render_template("explore.html", combined_map_data=json.dumps(all_map_data))

@main_bp.route('/help')
def help():
    return render_template('help.html')