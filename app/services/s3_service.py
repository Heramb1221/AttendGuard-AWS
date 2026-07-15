"""
Thin wrapper around boto3's S3 client for uploading generated attendance
reports and returning time-limited pre-signed download URLs.

NOTE ON boto3 API CORRECTNESS:
This module intentionally does NOT touch bucket CORS configuration.
If CORS is ever added here in the future, the correct boto3 call is:
    s3_client.put_bucket_cors(Bucket=..., CORSConfiguration={...})
NOT `put_bucket_cors_configuration`, which does not exist on the boto3 S3
client and will raise an AttributeError.
"""
import boto3
from botocore.exceptions import ClientError

from app.utils.logger import get_logger

logger = get_logger("s3_service")


class S3ReportService:
    def __init__(self, bucket_name: str, region_name: str):
        if not bucket_name:
            raise ValueError(
                "S3_REPORTS_BUCKET is not configured. Set it in your .env file."
            )
        self.bucket_name = bucket_name
        self.client = boto3.client("s3", region_name=region_name)

    def upload_report(self, local_file_path: str, s3_key: str) -> str:
        """Upload a local file to S3 under the given key. Returns the key."""
        try:
            self.client.upload_file(local_file_path, self.bucket_name, s3_key)
            logger.info("Uploaded report to s3://%s/%s", self.bucket_name, s3_key)
            return s3_key
        except ClientError:
            logger.exception("Failed to upload report to S3")
            raise

    def generate_download_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Return a pre-signed URL valid for `expires_in` seconds."""
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expires_in,
            )
        except ClientError:
            logger.exception("Failed to generate pre-signed URL for %s", s3_key)
            raise
