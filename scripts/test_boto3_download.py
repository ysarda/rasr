import boto3
from botocore import UNSIGNED
from botocore.client import Config
from datetime import datetime

# Create S3 client with proper configuration
s3_client = boto3.client('s3',
                         region_name='us-east-1',
                         config=Config(signature_version=UNSIGNED,
                                      user_agent_extra='Resource'))

bucket_name = 'unidata-nexrad-level2'

# List available years
def get_available_years():
    response = s3_client.list_objects_v2(
        Bucket=bucket_name,
        Delimiter='/',
        Prefix=''
    )
    years = [prefix['Prefix'].strip('/') 
             for prefix in response.get('CommonPrefixes', [])]
    return sorted(years)

# Get files for a specific station and date
def get_station_files(station, year, month, day):
    """
    station: e.g., 'KTLX'
    year, month, day: strings like '2024', '01', '15'
    """
    prefix = f"{year}/{month}/{day}/{station}/"
    
    files = []
    paginator = s3_client.get_paginator('list_objects_v2')
    
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        if 'Contents' in page:
            files.extend([obj['Key'] for obj in page['Contents']])
    
    return files

# Download a file
def download_file(s3_key, local_path):
    s3_client.download_file(bucket_name, s3_key, local_path)
    print(f"Downloaded: {local_path}")

# Example usage
years = get_available_years()
print(f"Available years: {years}")

# Get files for KTLX on Jan 1, 2024
files = get_station_files('KTLX', '2024', '01', '01')
print(f"Found {len(files)} files for KTLX on 2024-01-01")

# Download first file
if files:
    filename = files[0].split('/')[-1]
    download_file(files[0], f'./data/{filename}')