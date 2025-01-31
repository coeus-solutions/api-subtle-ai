import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from app.core.config import settings
import logging
import requests

logger = logging.getLogger(__name__)

def get_s3_client():
    """Get an S3 client configured for Supabase storage."""
    config = Config(
        region_name=settings.SUPABASE_S3_REGION,
        signature_version='v4',
        retries={
            'max_attempts': 3,
            'mode': 'standard'
        }
    )
    
    return boto3.client(
        's3',
        endpoint_url=f"https://{settings.SUPABASE_S3_ENDPOINT}/s3",
        aws_access_key_id=settings.SUPABASE_S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.SUPABASE_S3_SECRET_ACCESS_KEY,
        region_name=settings.SUPABASE_S3_REGION,
        config=config
    )

def ensure_bucket_exists(s3_client, bucket_name: str):
    """Ensure the storage bucket exists."""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == '404':
            # Bucket doesn't exist, create it
            try:
                s3_client.create_bucket(Bucket=bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
            except Exception as create_error:
                logger.error(f"Error creating bucket: {str(create_error)}")
                raise
        else:
            logger.error(f"Error checking bucket: {str(e)}")
            raise

def upload_file(file_path: str, content: bytes, content_type: str = None) -> bool:
    """
    Upload a file to Supabase storage.
    Returns True if successful, False otherwise.
    """
    try:
        s3_client = get_s3_client()
        extra_args = {'ContentType': content_type} if content_type else {}
        
        # Add debug logging
        logger.info(f"Uploading file: {file_path}")
        logger.info(f"Bucket: {settings.STORAGE_BUCKET}")
        logger.info(f"Content Type: {content_type}")
        
        s3_client.put_object(
            Bucket=settings.STORAGE_BUCKET,
            Key=file_path,
            Body=content,
            **extra_args
        )
        return True
    except Exception as e:
        logger.error(f"Error uploading file {file_path}: {str(e)}")
        return False

def delete_file(file_path: str) -> bool:
    """
    Delete a file from Supabase storage.
    Returns True if successful, False otherwise.
    """
    try:
        s3_client = get_s3_client()
        
        # Add debug logging
        logger.info(f"Attempting to delete file: {file_path}")
        logger.info(f"Bucket: {settings.STORAGE_BUCKET}")
        
        # Check if file exists before deleting
        try:
            s3_client.head_object(Bucket=settings.STORAGE_BUCKET, Key=file_path)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.warning(f"File {file_path} does not exist in bucket")
                return False
            else:
                raise
        
        # Delete the file
        s3_client.delete_object(
            Bucket=settings.STORAGE_BUCKET,
            Key=file_path
        )
        logger.info(f"Successfully deleted file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        return False

def download_file(file_path: str, destination_path: str) -> bool:
    """
    Download a file from Supabase storage.
    Returns True if successful, False otherwise.
    """
    try:
        s3_client = get_s3_client()
        s3_client.download_file(
            Bucket=settings.STORAGE_BUCKET,
            Key=file_path,
            Filename=destination_path
        )
        return True
    except Exception as e:
        logger.error(f"Error downloading file {file_path}: {str(e)}")
        return False

def get_file_url(file_path: str) -> str:
    """Generate the public URL for a file."""
    return f"{settings.SUPABASE_STORAGE_URL}/object/public/{settings.STORAGE_BUCKET}/{file_path}"

# Note: For Supabase storage, we don't need to check/create buckets as they are managed by Supabase
# The bucket should be created through the Supabase dashboard 