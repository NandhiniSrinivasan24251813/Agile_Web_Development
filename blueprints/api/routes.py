# blueprints/api/routes.py
from flask import jsonify, request, abort
from flask_login import current_user, login_required
from models import db, Dataset, EpidemicRecord
from . import api_bp
import json

# API endpoints can be added here

@api_bp.route('/datasets')
@login_required
def get_datasets():
    # Return a list of user's datasets
    datasets = Dataset.query.filter_by(user_id=current_user.id).all()
    
    result = []
    for dataset in datasets:
        result.append({
            'id': dataset.id,
            'name': dataset.name,
            'description': dataset.description,
            'record_count': dataset.record_count,
            'upload_date': dataset.upload_date.isoformat() if dataset.upload_date else None,
            'sharing_status': dataset.sharing_status
        })
    
    return jsonify(result)

@api_bp.route('/datasets/<int:dataset_id>')
@login_required
def get_dataset(dataset_id):
    # Get a specific dataset
    dataset = Dataset.query.get_or_404(dataset_id)
    
    # Check permissions
    if dataset.user_id != current_user.id and dataset.sharing_status != 'public':
        abort(403)
    
    # Get data
    data = dataset.get_data()
    
    result = {
        'id': dataset.id,
        'name': dataset.name,
        'description': dataset.description,
        'record_count': dataset.record_count,
        'upload_date': dataset.upload_date.isoformat() if dataset.upload_date else None,
        'sharing_status': dataset.sharing_status,
        'data': data[:100]  # First 100 records only for preview
    }
    
    return jsonify(result)