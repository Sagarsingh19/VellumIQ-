import os
import shutil
from abc import ABC, abstractmethod
from typing import BinaryIO
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

class StorageBackend(ABC):
    @abstractmethod
    def upload_file(self, file_obj: BinaryIO, object_name: str) -> None:
        """Uploads a file object to the storage backend."""
        pass

    @abstractmethod
    def generate_presigned_url(self, object_name: str, expiration: int = 900) -> str:
        """Generates a temporary pre-signed URL to read the file."""
        pass

    @abstractmethod
    def download_file(self, object_name: str, dest_path: str) -> None:
        """Downloads a file from storage to the local destination path."""
        pass


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: str = "storage_local"):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_full_path(self, object_name: str) -> str:
        # Prevent directory traversal attacks
        safe_name = os.path.normpath(object_name).lstrip(os.path.sep)
        full_path = os.path.join(self.base_dir, safe_name)
        if not full_path.startswith(self.base_dir):
            raise ValueError("Directory traversal attempt detected.")
        return full_path

    def upload_file(self, file_obj: BinaryIO, object_name: str) -> None:
        full_path = self._get_full_path(object_name)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            shutil.copyfileobj(file_obj, f)

    def generate_presigned_url(self, object_name: str, expiration: int = 900) -> str:
        # For local, we generate a link pointing to our local file delivery API.
        # Example format: /api/v1/documents/local-file/{object_name}
        # In a real environment, you'd prepend the server hostname.
        safe_name = object_name.replace("\\", "/")
        return f"/api/v1/documents/local-file/{safe_name}"

    def download_file(self, object_name: str, dest_path: str) -> None:
        full_path = self._get_full_path(object_name)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File {object_name} not found locally.")
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(full_path, dest_path)


class S3StorageBackend(StorageBackend):
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        
        # Configure client connection
        s3_config = Config(signature_version="s3v4")
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=s3_config,
            use_ssl=settings.S3_SECURE,
        )
        
        # Auto-initialize bucket if it doesn't exist
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                self.client.create_bucket(Bucket=self.bucket_name)
            else:
                raise e

    def upload_file(self, file_obj: BinaryIO, object_name: str) -> None:
        try:
            self.client.upload_fileobj(file_obj, self.bucket_name, object_name)
        except ClientError as e:
            raise RuntimeError(f"Failed to upload to S3: {str(e)}")

    def generate_presigned_url(self, object_name: str, expiration: int = 900) -> str:
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_name},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            raise RuntimeError(f"Failed to generate pre-signed URL: {str(e)}")

    def download_file(self, object_name: str, dest_path: str) -> None:
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            self.client.download_file(self.bucket_name, object_name, dest_path)
        except ClientError as e:
            raise RuntimeError(f"Failed to download from S3: {str(e)}")


def get_storage_client() -> StorageBackend:
    """Returns the storage backend client configured in the settings."""
    if settings.STORAGE_BACKEND == "s3":
        return S3StorageBackend()
    return LocalStorageBackend()


# Global storage instance
storage_client = get_storage_client()
