import boto3
from botocore.exceptions import ClientError
from django.conf import settings
import structlog

logger = structlog.get_logger(__name__)

class StorageService:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    def upload_file(self, file_content, file_name, content_type="application/pdf"):
        """Uploads a file to MinIO/S3 with a local fallback for development."""
        try:
            # 1. Try S3/MinIO first
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=file_content,
                ContentType=content_type,
            )
            
            # Generate a URL for the file
            url = f"{settings.AWS_S3_ENDPOINT_URL}/{self.bucket_name}/{file_name}"
            logger.info("file_uploaded_s3", bucket=self.bucket_name, key=file_name, url=url)
            return url
        except Exception as e:
            logger.warning("s3_upload_failed_falling_back_to_local", error=str(e))
            
            # 2. Local Fallback (Development only or Emergency)
            try:
                import os # noqa: PLC0415
                from django.conf import settings # noqa: PLC0415
                
                # Use a specific directory for reports in media
                local_path = os.path.join(settings.BASE_DIR, "media", file_name)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                mode = "wb" if isinstance(file_content, (bytes, bytearray)) else "w"
                with open(local_path, mode) as f:
                    f.write(file_content)
                
                # Construct local URL (assumes /media/ is served)
                local_url = f"{settings.FRONTEND_URL.replace(':3000', ':8000')}/media/{file_name}"
                logger.info("file_uploaded_local", path=local_path, url=local_url)
                return local_url
            except Exception as local_e:
                logger.error("local_storage_failed", error=str(local_e))
                return None

    def get_signed_url(self, file_name, expires_in=3600):
        """Generates a presigned URL for a file."""
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_name},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error("presigned_url_failed", error=str(e), key=file_name)
            return None

    def ensure_bucket_exists(self):
        """Checks if the bucket exists, creates it if not."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                logger.info("creating_bucket", bucket=self.bucket_name)
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                logger.error("bucket_check_failed", error=str(e), bucket=self.bucket_name)
                raise
