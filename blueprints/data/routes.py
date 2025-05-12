# blueprints/data/routes.py
from flask import render_template, redirect, send_file, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from models import db, User, AuditLog, Dataset, EpidemicRecord, SharedDataset
from werkzeug.utils import secure_filename
from data_bridge import DataBridge
from utils import DataConverter
from . import data_bp
# from app import app, logger
from flask import current_app
import os
import pandas as pd
import numpy as np
import json
import io
from datetime import datetime, timezone
import threading
from queue import Queue
import time


# ---------------------------------------------------------
# Upload Route
# ---------------------------------------------------------
@data_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # Save the file temporarily
                filename = secure_filename(file.filename)
                temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f'temp_{filename}')
                file.save(temp_path)
                
                # Detect file format
                file_format = DataConverter.detect_file_type(temp_path)
                
                # Create dataset record
                dataset = Dataset(
                    name=request.form.get('name', filename),
                    description=request.form.get('description', ''),
                    original_filename=filename,
                    original_format=file_format,
                    user_id=current_user.id,
                    sharing_status = request.form.get('sharing_status', 'private')
                )
                
                # Try using the new unified storage approach
                try:
                    # Convert file to standardized JSON format
                    data, metadata = DataBridge.file_to_standardized_data(temp_path, file_format)
                    
                    # Update dataset with standardized data and metadata
                    dataset.set_data(data)
                    
                    if 'record_count' in metadata:
                        dataset.record_count = metadata['record_count']
                    if 'has_geo' in metadata:
                        dataset.has_geo = metadata['has_geo']
                    if 'has_time' in metadata:
                        dataset.has_time = metadata['has_time']
                    if 'date_range_start' in metadata:
                        dataset.date_range_start = metadata['date_range_start']
                    if 'date_range_end' in metadata:
                        dataset.date_range_end = metadata['date_range_end']
                    
                    # Save dataset to database
                    db.session.add(dataset)
                    db.session.commit()
                    
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
                    # Log the activity
                    audit = AuditLog(
                        user_id=current_user.id,
                        action="upload_dataset",
                        target_type="Dataset",
                        target_id=dataset.id,
                        details=f"Uploaded dataset '{dataset.name}' with {dataset.record_count} records"
                    )
                    db.session.add(audit)
                    db.session.commit()
                    
                    flash('Dataset uploaded and processed successfully!', 'success')
                    return redirect(url_for('data.visualize', dataset_id=dataset.id))
                
                except Exception as e:
                    # If the new approach fails, fall back to the legacy method
                    current_app.logger.warning(f"Error using unified JSON storage: {str(e)}")
                    current_app.logger.info("Falling back to legacy record processing...")
                    
                    try:
                        # Save the dataset without JSON data first
                        db.session.add(dataset)
                        db.session.commit()
                        
                        # Process the file based on its type using your existing method
                        if file_format == 'csv':
                            # Read CSV in chunks
                            chunks = pd.read_csv(temp_path, chunksize=current_app.config['BATCH_SIZE'])
                            for chunk in chunks:
                                records = chunk.to_dict('records')
                                process_batch(records, dataset.id, current_user.id)
                                
                        elif file_format == 'json':
                            # Read JSON
                            with open(temp_path, 'r') as f:
                                records = json.load(f)
                            process_batch(records, dataset.id, current_user.id)
                            
                        elif file_format in ['excel', 'xlsx', 'xls']:
                            # Read Excel
                            df = pd.read_excel(temp_path)
                            records = df.to_dict('records')
                            process_batch(records, dataset.id, current_user.id)
                        
                        # Update record count
                        count = EpidemicRecord.query.filter_by(dataset_id=dataset.id).count()
                        dataset.record_count = count
                        db.session.commit()
                        
                        # Clean up temporary file
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        
                        # Log the activity
                        audit = AuditLog(
                            user_id=current_user.id,
                            action="upload_dataset_legacy",
                            target_type="Dataset",
                            target_id=dataset.id,
                            details=f"Uploaded dataset '{dataset.name}' with legacy processing"
                        )
                        db.session.add(audit)
                        db.session.commit()
                        
                        flash('Dataset uploaded successfully (using legacy processing).', 'success')
                        return redirect(url_for('main.dashboard'))
                    
                    except Exception as legacy_error:
                        db.session.rollback()
                        current_app.logger.error(f"Legacy processing also failed: {str(legacy_error)}")
                        flash(f'Error processing file: {str(legacy_error)}', 'error')
                        
                        # Clean up temporary file
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                            
                        return redirect(request.url)
                        
            except Exception as e:
                db.session.rollback()
                flash(f'Error uploading file: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Invalid file type. Please upload CSV, JSON, or Excel files.', 'error')
            return redirect(request.url)
    
    return render_template('upload.html')

# ---------------------------------------------------------
# Export Route
# ---------------------------------------------------------
@data_bp.route('/export/<int:dataset_id>')
@login_required
def export_dataset(dataset_id):
    # Get dataset
    dataset = db.session.get(Dataset, dataset_id)
    
    # Check permission
    is_owner = dataset.user_id == current_user.id
    is_shared = SharedDataset.query.filter_by(dataset_id=dataset_id, shared_with_id=current_user.id).first() is not None
    is_public = dataset.sharing_status == 'public'
    
    if not (is_owner or is_shared or is_public):
        flash('You do not have permission to download this dataset', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get export format
    export_format = request.args.get('format', 'csv')
    if export_format not in ['csv', 'json', 'excel', 'xlsx']:
        flash('Unsupported export format', 'error')
        return redirect(url_for('data.visualize', dataset_id=dataset_id))
    
    try:
        # Get data from dataset using the unified storage
        data = dataset.get_data()
        
        if not data:
            flash('Dataset is empty', 'error')
            return redirect(url_for('data.visualize', dataset_id=dataset_id))
        
        # Generate filename
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        base_name = os.path.splitext(dataset.original_filename)[0]
        
        if export_format == 'csv':
            filename = f"{base_name}_{timestamp}.csv"
            mimetype = 'text/csv'
            
            # Convert data to CSV
            output = DataBridge.data_to_format(data, 'csv')
            
            return send_file(
                io.BytesIO(output.encode('utf-8')),
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
        
        elif export_format == 'json':
            filename = f"{base_name}_{timestamp}.json"
            mimetype = 'application/json'
            
            # Convert data to JSON
            output = DataBridge.data_to_format(data, 'json')
            
            return send_file(
                io.BytesIO(output.encode('utf-8')),
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
        
        elif export_format in ['excel', 'xlsx']:
            filename = f"{base_name}_{timestamp}.xlsx"
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            
            # Convert data to Excel (returns BytesIO)
            output = DataBridge.data_to_format(data, 'excel')
            
            return send_file(
                output,
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
            
    except Exception as e:
        current_app.logger.error(f"Error exporting dataset: {str(e)}")
        flash(f'Error exporting dataset: {str(e)}', 'error')
        return redirect(url_for('data.visualize', dataset_id=dataset_id))


# ---------------------------------------------------------
# Visualize Route
# ---------------------------------------------------------
@data_bp.route('/visualize/<int:dataset_id>')
def visualize(dataset_id):
    dataset = db.session.get(Dataset, dataset_id)

    # Check access permissions
    is_owner = current_user.is_authenticated and dataset.user_id == current_user.id
    is_shared = current_user.is_authenticated and SharedDataset.query.filter_by(
        dataset_id=dataset_id,
        shared_with_id=current_user.id
    ).first() is not None
    is_public = dataset.sharing_status == 'public'

    if not (is_owner or is_shared or is_public):
        if current_user.is_authenticated:
            flash('You do not have permission to view this dataset', 'error')
            return redirect(url_for('main.dashboard'))
        else:
            abort(403)

    # Process records for visualization
    records = dataset.get_data()
    map_data, trend_data = [], []

    if records:
        for record in records:
            if 'latitude' in record and 'longitude' in record:
                try:
                    lat = float(record['latitude'])
                    lng = float(record['longitude'])
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        map_data.append({
                            'location': record.get('location', 'Unknown'),
                            'latitude': lat,
                            'longitude': lng,
                            'cases': record.get('cases', 0),
                            'deaths': record.get('deaths', 0),
                            'recovered': record.get('recovered', 0),
                            'date': record.get('date')
                        })
                except (ValueError, TypeError):
                    pass

        # Group records by date
        date_groups = {}
        for record in records:
            date = record.get('date', 'Unknown')
            date_groups.setdefault(date, {'date': date, 'cases': 0, 'deaths': 0, 'recovered': 0})
            date_groups[date]['cases'] += record.get('cases', 0)
            date_groups[date]['deaths'] += record.get('deaths', 0)
            date_groups[date]['recovered'] += record.get('recovered', 0)
        trend_data = sorted(date_groups.values(), key=lambda x: x['date'])

    preview_data = records[:10] if records else []
    preview_columns = ['location', 'date', 'cases', 'deaths', 'recovered']
    numeric_fields = ['cases', 'deaths', 'recovered']

    if any('tested' in r for r in preview_data):
        preview_columns.append('tested')
        numeric_fields.append('tested')
    if any('hospitalized' in r for r in preview_data):
        preview_columns.append('hospitalized')
        numeric_fields.append('hospitalized')

    total_cases = sum(r.get('cases', 0) for r in records)
    total_deaths = sum(r.get('deaths', 0) for r in records)
    total_recovered = sum(r.get('recovered', 0) for r in records)
    summary_stats = {
        'total cases': f"{total_cases:,}",
        'total deaths': f"{total_deaths:,}",
        'total recovered': f"{total_recovered:,}",
        'case fatality rate': f"{(total_deaths / total_cases * 100):.2f}%" if total_cases else "N/A",
        'recovery rate': f"{(total_recovered / total_cases * 100):.2f}%" if total_cases else "N/A"
    }

    date_range = f"{dataset.date_range_start:%Y-%m-%d} to {dataset.date_range_end:%Y-%m-%d}" if dataset.date_range_start and dataset.date_range_end else "N/A"

    return render_template(
        'visualize.html',
        dataset=dataset,
        map_data=json.dumps(map_data),
        trend_data=json.dumps(trend_data),
        preview_data=preview_data,
        preview_columns=preview_columns,
        numeric_fields=numeric_fields,
        summary_stats=summary_stats,
        columns=numeric_fields,
        date_range=date_range,
        visualization_title=dataset.name,
        trend_analysis="Data shows fluctuations in case numbers over time with notable peaks during outbreak periods.",
        key_observations=[
            "Highest case numbers were reported in densely populated areas.",
            "Recovery rates improved significantly in later time periods.",
            "Regional differences in case fatality rates may indicate varying healthcare capacities."
        ]
    )

# Add a debug endpoint to inspect file content
@data_bp.route('/debug_file/<int:dataset_id>')
@login_required
def debug_file(dataset_id):
    # Check if user is admin or file owner
    dataset = db.session.get(Dataset, dataset_id)
    
    if dataset.user_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Check file type and read preview
        if dataset.filepath and os.path.exists(dataset.filepath):
            if dataset.file_type == 'text/csv' or dataset.filename.endswith('.csv'):
                # Read first few rows of CSV
                df = pd.read_csv(dataset.filepath, nrows=5)
                column_names = df.columns.tolist()
                sample_data = df.head(5).to_dict('records')
                
                return render_template('debug_file.html', 
                                      dataset=dataset,
                                      column_names=column_names,
                                      sample_data=sample_data,
                                      file_type='CSV')
                
            elif dataset.file_type == 'application/json' or dataset.filename.endswith('.json'):
                # Read first few records of JSON
                with open(dataset.filepath, 'r') as f:
                    json_data = []
                    for i, line in enumerate(f):
                        if i >= 5:  # Read up to 5 lines
                            break
                        if line.strip():
                            json_data.append(json.loads(line))
                
                # Get column names from first record if available
                column_names = []
                if json_data:
                    column_names = list(json_data[0].keys())
                
                return render_template('debug_file.html',
                                     dataset=dataset,
                                     column_names=column_names,
                                     sample_data=json_data,
                                     file_type='JSON')
        
        flash('File not found or unsupported format', 'error')
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        flash(f'Error inspecting file: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))

@data_bp.route('/delete_dataset/<int:dataset_id>', methods=['POST'])
@login_required
def delete_dataset(dataset_id):
    dataset = db.session.get(Dataset, dataset_id)
    
    # Check permissions
    if dataset.user_id != current_user.id:
        flash('You do not have permission to delete this dataset.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Delete any legacy EpidemicRecord entries (for backward compatibility)
        EpidemicRecord.query.filter_by(dataset_id=dataset.id).delete()
        
        # Delete any SharedDataset entries referencing this dataset
        SharedDataset.query.filter_by(dataset_id=dataset.id).delete()
        
        # Delete the dataset itself (the data_json field will be deleted automatically)
        db.session.delete(dataset)
        
        # Commit all changes
        db.session.commit()
        
        # Log the deletion
        audit = AuditLog(
            user_id=current_user.id,
            action="delete_dataset",
            target_type="Dataset",
            target_id=dataset.id,
            details=f"Deleted dataset '{dataset.name}'"
        )
        db.session.add(audit)
        db.session.commit()
        
        flash('Dataset deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting dataset: {str(e)}', 'error')
        
    return redirect(url_for('main.dashboard'))

@data_bp.route('/share/<int:dataset_id>', methods=['POST'])
@login_required
# @csrf.exempt
def share_dataset(dataset_id):
    email = request.form['email']
    permission = request.form.get('permission', 'read')
    
    # Find the user by email
    user_to_share = User.query.filter_by(email=email).first()
    if user_to_share:
        shared = SharedDataset(
            # owner_id=current_user.id,
            shared_by_id = current_user.id,
            shared_with_id=user_to_share.id,
            dataset_id=dataset_id,
        )
        db.session.add(shared)
        db.session.commit()
        flash(f"Dataset shared with {email}.", "success")
    else:
        flash("User not found.", "danger")
    
    return redirect(url_for('main.dashboard'))


# Charts Route
@data_bp.route('/charts/<int:dataset_id>')
@login_required
def view_charts(dataset_id):
    dataset = db.session.get(Dataset, dataset_id)

    # Permission check
    is_owner = dataset.user_id == current_user.id
    is_shared = SharedDataset.query.filter_by(dataset_id=dataset_id, shared_with_id=current_user.id).first() is not None
    is_public = dataset.sharing_status == 'public'

    if not (is_owner or is_shared or is_public):
        flash('You do not have permission to view this chart', 'error')
        return redirect(url_for('main.dashboard'))

    records = dataset.get_data() or []
    chart_fields = ['cases', 'deaths', 'recovered']
    if any('tested' in r for r in records):
        chart_fields.append('tested')
    if any('hospitalized' in r for r in records):
        chart_fields.append('hospitalized')

    # Filter for time series chart: keep only records with valid dates
    chart_data = [r for r in records if 'date' in r and r['date']]

    return render_template(
        'charts.html',
        dataset=dataset,
        chart_data=json.dumps(chart_data),
        chart_fields=chart_fields
    )

# --------------------------------------------
# Helper Functions
# --------------------------------------------
def allowed_file(filename):
    """Check if the file has an allowed extension"""
    ALLOWED_EXTENSIONS = {'csv', 'json', 'xlsx', 'xls'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Add this function for batch processing
def process_batch(records, dataset_id, user_id):
    try:
        epidemic_records = []
        for record in records:
            lat = record.get('latitude') or record.get('lat') or None
            lon = record.get('longitude') or record.get('long') or record.get('lon') or record.get('lng') or None
            epidemic_record = EpidemicRecord(
                dataset_id=dataset_id,
                date=record.get('date') or record.get('Date') or None,
                location=record.get('location') or record.get('Location') or record.get('region') or record.get('Region') or None,
                cases=record.get('cases') or record.get('Cases') or record.get('confirmed') or record.get('Confirmed') or 0,
                deaths=record.get('deaths') or record.get('Deaths') or 0,
                recovered=record.get('recovered') or record.get('Recovered') or 0,
                latitude=lat,
                longitude=lon
            )
            epidemic_records.append(epidemic_record)
        
        if any(rec.latitude is not None and rec.longitude is not None for rec in epidemic_records):
            dataset = db.session.get(Dataset, dataset_id)
            if dataset:
                dataset.has_geo = True
                db.session.commit()
        
        db.session.bulk_save_objects(epidemic_records)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        return str(e)

# Add this function for chunked file reading
def read_file_in_chunks(file_path):
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(current_app.config['CHUNK_SIZE'])
            if not chunk:
                break
            yield chunk