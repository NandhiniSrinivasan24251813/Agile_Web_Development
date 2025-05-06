# utils.py
import pandas as pd
import json
import io
import datetime
import numpy as np
import os

#--------------------------------------------------------------------------------
class DataConverter:
    """Utility class for converting between different data formats"""
    
    @staticmethod
    def standardize_column_names(df):
        """Standardize column names to lowercase and handle common variations"""
        # Test columns
        column_maps = {
            'date': ['date', 'datetime', 'day', 'report_date'],
            'location': ['location', 'place', 'region', 'area', 'country', 'state', 'city'],
            'cases': ['cases', 'confirmed', 'confirmed_cases', 'total_cases', 'positives'],
            'deaths': ['deaths', 'fatalities', 'total_deaths', 'deceased'],
            'recovered': ['recovered', 'total_recovered', 'recoveries'],
            'latitude': ['latitude', 'lat', 'y'],
            'longitude': ['longitude', 'long', 'lon', 'lng', 'x'],
            'tested': ['tested', 'tests', 'total_tested'],
            'hospitalized': ['hospitalized', 'hospitalizations', 'hospital'],
            'severity': ['severity', 'case_severity', 'condition'],
            'postcode': ['postcode', 'zip', 'zipcode', 'postal_code'],
            'country': ['country', 'nation'],
            'region': ['region', 'province', 'state', 'territory']
        }
        
        # Create lowercased column names
        df.columns = [col.lower() for col in df.columns]
        
        # Rename columns based on matches
        for standard_name, variations in column_maps.items():
            for column in df.columns:
                if column in variations and column != standard_name:
                    df.rename(columns={column: standard_name}, inplace=True)
                    break
        
        return df
    
#---------------------------------------------------------------------------------
    @staticmethod
    def ensure_required_columns(df):
        """Ensure the dataframe has all required columns, adding empty ones if needed"""
        required_columns = ['date', 'location', 'cases']
        
        for col in required_columns:
            if col not in df.columns:
                if col == 'date':
                    df[col] = pd.Timestamp('today').strftime('%Y-%m-%d')
                elif col == 'location':
                    df[col] = 'Unknown'
                else:
                    df[col] = 0
        
        return df
    
#---------------------------------------------------------------------------------   
    @staticmethod
    def fix_data_types(df):
        """Fix data types for standard columns"""
        # Convert date strings to datetime objects
        if 'date' in df.columns:
            try:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            except Exception:
                df['date'] = pd.Timestamp('today').strftime('%Y-%m-%d')
        
        # Convert numeric columns
        numeric_cols = ['cases', 'deaths', 'recovered', 'tested', 'hospitalized']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        # Convert lat/long to float
        geo_cols = ['latitude', 'longitude']
        for col in geo_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
#---------------------------------------------------------------------------------    
    @staticmethod
    def preprocess_dataframe(df):
        """Apply all preprocessing steps to standardize the dataframe"""
        df = DataConverter.standardize_column_names(df)
        df = DataConverter.ensure_required_columns(df)
        df = DataConverter.fix_data_types(df)
        return df

#---------------------------------------------------------------------------------    
    @staticmethod
    def csv_to_json(file_path, output_path=None):
        """Convert CSV file to standardized JSON format"""
        try:
            # Read CSV in chunks if large
            chunk_size = 10000
            chunks = pd.read_csv(file_path, chunksize=chunk_size)
            
            all_data = []
            for chunk in chunks:
                # Preprocess the chunk
                chunk = DataConverter.preprocess_dataframe(chunk)
                
                # Convert to records format (list of dicts)
                records = chunk.to_dict('records')
                all_data.extend(records)
            
            # Save if output path provided
            if output_path:
                with open(output_path, 'w') as f:
                    json.dump(all_data, f, cls=JSONEncoder)
            
            return all_data
            
        except Exception as e:
            print(f"Error converting CSV to JSON: {str(e)}")
            return None
    
#---------------------------------------------------------------------------------    
    @staticmethod
    def excel_to_json(file_path, output_path=None):
        """Convert Excel file to standardized JSON format"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Preprocess the dataframe
            df = DataConverter.preprocess_dataframe(df)
            
            # Convert to records format (list of dicts)
            records = df.to_dict('records')
            
            # Save if output path provided
            if output_path:
                with open(output_path, 'w') as f:
                    json.dump(records, f, cls=JSONEncoder)
            
            return records
            
        except Exception as e:
            print(f"Error converting Excel to JSON: {str(e)}")
            return None
    
#---------------------------------------------------------------------------------    
    @staticmethod
    def json_to_json(file_path, output_path=None):
        """Standardize JSON format"""
        try:
            # Read JSON file
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Convert to DataFrame for preprocessing
            df = pd.DataFrame(data)
            
            # Preprocess the dataframe
            df = DataConverter.preprocess_dataframe(df)
            
            # Convert back to records
            records = df.to_dict('records')
            
            # Save if output path provided
            if output_path:
                with open(output_path, 'w') as f:
                    json.dump(records, f, cls=JSONEncoder)
            
            return records
            
        except Exception as e:
            print(f"Error standardizing JSON: {str(e)}")
            return None
    
#---------------------------------------------------------------------------------    
    @staticmethod
    def json_to_csv(data, output_path=None):
        """Convert JSON data to CSV format"""
        try:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Save to CSV if output path provided
            if output_path:
                df.to_csv(output_path, index=False)
            
            # Return CSV as string if no output path
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            return csv_buffer.getvalue()
            
        except Exception as e:
            print(f"Error converting JSON to CSV: {str(e)}")
            return None
    
#---------------------------------------------------------------------------------    
    @staticmethod
    def json_to_excel(data, output_path=None):
        """Convert JSON data to Excel format"""
        try:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Save to Excel if output path provided
            if output_path:
                df.to_excel(output_path, index=False)
                return True
            
            # Return Excel as bytes if no output path
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False)
            return excel_buffer.getvalue()
            
        except Exception as e:
            print(f"Error converting JSON to Excel: {str(e)}")
            return None
    
#---------------------------------------------------------------------------------    
    @staticmethod
    def detect_file_type(file_path):
        """Detect file type based on extension"""
        extension = os.path.splitext(file_path)[1].lower()
        
        if extension == '.csv':
            return 'csv'
        elif extension in ['.xls', '.xlsx']:
            return 'excel'
        elif extension == '.json':
            return 'json'
        else:
            return None
        
#---------------------------------------------------------------------------------    
    @staticmethod
    def convert_to_json(file_path, output_path=None):
        """Convert any supported file to standardized JSON"""
        file_type = DataConverter.detect_file_type(file_path)
        
        if file_type == 'csv':
            return DataConverter.csv_to_json(file_path, output_path)
        elif file_type == 'excel':
            return DataConverter.excel_to_json(file_path, output_path)
        elif file_type == 'json':
            return DataConverter.json_to_json(file_path, output_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
#---------------------------------------------------------------------------------    
    @staticmethod
    def export_from_json(data, format_type, output_path=None):
        """Export JSON data to specified format"""
        if format_type == 'csv':
            return DataConverter.json_to_csv(data, output_path)
        elif format_type == 'excel' or format_type == 'xlsx':
            return DataConverter.json_to_excel(data, output_path)
        elif format_type == 'json':
            if output_path:
                with open(output_path, 'w') as f:
                    json.dump(data, f, cls=JSONEncoder)
                return True
            return json.dumps(data, cls=JSONEncoder)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

#---------------------------------------------------------------------------------
class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle date/time objects and other special types"""
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super().default(obj)