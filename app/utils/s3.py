import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from app.core.config import settings

def ensure_bucket_exists(s3_client, bucket_name: str):
    """Ensure the specified bucket exists, create it if it doesn't."""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == '404' or error_code == 'NoSuchBucket':
            # Bucket doesn't exist, create it
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': settings.SUPABASE_S3_REGION
                }
            )
            # Make bucket public
            s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': False,
                    'IgnorePublicAcls': False,
                    'BlockPublicPolicy': False,
                    'RestrictPublicBuckets': False
                }
            )
            # Add bucket policy for public read access
            bucket_policy = {
                'Version': '2012-10-17',
                'Statement': [{
                    'Sid': 'PublicReadGetObject',
                    'Effect': 'Allow',
                    'Principal': '*',
                    'Action': ['s3:GetObject'],
                    'Resource': [f'arn:aws:s3:::{bucket_name}/*']
                }]
            }
            s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=str(bucket_policy)
            )

def get_s3_client():
    """Get an S3 client configured for Supabase storage."""
    config = Config(
        region_name=settings.SUPABASE_S3_REGION,
        signature_version='v4'
    )
    
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.SUPABASE_S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.SUPABASE_S3_SECRET_ACCESS_KEY,
        endpoint_url=settings.SUPABASE_STORAGE_URL,
        config=config
    )
    
    # Ensure the bucket exists
    ensure_bucket_exists(s3_client, settings.STORAGE_BUCKET)
    
    return s3_client 