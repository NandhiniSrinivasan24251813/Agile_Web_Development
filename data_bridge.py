import pandas as pd
import json
import io
import datetime
from utils import DataConverter, JSONEncoder
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('data_bridge')

#--
class DataBridge:
    @staticmethod
    def file_to_standardized_data(file_path, file_format=None):

        # Use the existing DataConverter to detect file type if not provided
        if not file_format:
            file_format = DataConverter.detect_file_type(file_path)
        
        data = []
        metadata = {
            'record_count': 0,
            'has_geo': False,
            'has_time': False
        }
        
        try:
            if file_format == 'csv':
                data = DataConverter.csv_to_json(file_path)
                
            elif file_format in ['excel', 'xlsx', 'xls']:
                data = DataConverter.excel_to_json(file_path)
                
            elif file_format == 'json':
                data = DataConverter.json_to_json(file_path)
            
            else:
                raise ValueError(f"Unsupported file type: {file_format}")
            metadata.update(DataBridge.extract_metadata(data))
            
            return data, metadata
            
        except Exception as e:
            logger.error(f"Error converting file to standardized data: {str(e)}")
            raise
    
    @staticmethod
    def extract_metadata(data):
        """Extract metadata from standardized data"""
        metadata = {
            'record_count': len(data) if data else 0,
            'has_geo': False,
            'has_time': False
        }
        
        if not data or not isinstance(data, list):
            return metadata
            
        metadata['has_geo'] = any(
            'latitude' in record and 'longitude' in record and 
            record['latitude'] is not None and record['longitude'] is not None
            for record in data
        )
        
        dates = []
        for record in data:
            if 'date' in record and record['date']:
                try:
                    # Parse the date
                    if isinstance(record['date'], str):
                        date_obj = datetime.datetime.strptime(record['date'], '%Y-%m-%d').date()
                    else:
                        date_obj = record['date']
                    dates.append(date_obj)
                except (ValueError, TypeError):
                    pass
        
        metadata['has_time'] = len(dates) > 0
        
        if dates:
            metadata['date_range_start'] = min(dates)
            metadata['date_range_end'] = max(dates)
        
        return metadata
    
    @staticmethod
    def data_to_format(data, format_type):
        """
        Convert standardized data to requested output format
        Uses existing DataConverter methods
        """
        try:
            if format_type == 'csv':
                return DataConverter.json_to_csv(data)
                
            elif format_type in ['excel', 'xlsx', 'xls']:
                output = io.BytesIO()
                DataConverter.json_to_excel(data, output_path=None)
                return output
                
            elif format_type == 'json':
                return json.dumps(data, cls=JSONEncoder)
            
            else:
                raise ValueError(f"Unsupported format: {format_type}")
        
        except Exception as e:
            logger.error(f"Error converting data to {format_type}: {str(e)}")
            raise