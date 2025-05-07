import os
import uuid
import logging
import shutil
from typing import Dict, List, Any, Optional, Union, BinaryIO, Tuple
import asyncio
import aiofiles
import aiofiles.os
import mimetypes
import hashlib
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import AzureError
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageError(Exception):
    """Base exception for storage service errors."""
    pass


class StorageService:
    """Abstract base class for storage services."""
    
    async def initialize(self):
        """Initialize the storage service."""
        pass
    
    async def store_file(
        self, 
        file_data: Union[bytes, BinaryIO, str], 
        file_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Store a file.
        
        Args:
            file_data: The file data (bytes, file-like object, or path)
            file_path: The path to store the file at
            content_type: The MIME type of the file
            metadata: Additional metadata to store with the file
            
        Returns:
            The path where the file was stored
        """
        raise NotImplementedError
    
    async def get_file(self, file_path: str) -> Tuple[bytes, Optional[Dict[str, str]]]:
        """
        Get a file.
        
        Args:
            file_path: The path to the file
            
        Returns:
            Tuple of (file_data, metadata)
        """
        raise NotImplementedError
    
    async def get_file_stream(self, file_path: str) -> Tuple[BinaryIO, Optional[Dict[str, str]]]:
        """
        Get a file as a stream.
        
        Args:
            file_path: The path to the file
            
        Returns:
            Tuple of (file_stream, metadata)
        """
        raise NotImplementedError
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file.
        
        Args:
            file_path: The path to the file
            
        Returns:
            True if the file was deleted, False otherwise
        """
        raise NotImplementedError
    
    async def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            file_path: The path to the file
            
        Returns:
            True if the file exists, False otherwise
        """
        raise NotImplementedError
    
    async def list_files(self, directory: str) -> List[Dict[str, Any]]:
        """
        List files in a directory.
        
        Args:
            directory: The directory to list files in
            
        Returns:
            List of file information dictionaries
        """
        raise NotImplementedError
    
    async def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Get a URL for a file.
        
        Args:
            file_path: The path to the file
            expires_in: Time in seconds until the URL expires
            
        Returns:
            A URL for accessing the file
        """
        raise NotImplementedError
    
    async def close(self):
        """Close the storage service and release any resources."""
        pass


class LocalStorageService(StorageService):
    """Storage service that stores files on the local filesystem."""
    
    def __init__(self, base_dir: str = None):
        """
        Initialize the local storage service.
        
        Args:
            base_dir: Base directory for file storage
        """
        self.base_dir = base_dir or settings.storage_path
    
    async def initialize(self):
        """Initialize the storage service."""
        # Ensure base directory exists
        os.makedirs(self.base_dir, exist_ok=True)
        logger.info(f"Initialized local storage service with base directory: {self.base_dir}")
    
    async def store_file(
        self, 
        file_data: Union[bytes, BinaryIO, str], 
        file_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Store a file locally.
        
        Args:
            file_data: The file data (bytes, file-like object, or path)
            file_path: The path to store the file at (relative to base_dir)
            content_type: The MIME type of the file (ignored for local storage)
            metadata: Additional metadata to store with the file
            
        Returns:
            The path where the file was stored (relative to base_dir)
        """
        full_path = os.path.join(self.base_dir, file_path)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        try:
            # Handle different input types
            if isinstance(file_data, bytes):
                async with aiofiles.open(full_path, 'wb') as f:
                    await f.write(file_data)
            elif isinstance(file_data, str):
                # Assume it's a path
                if os.path.exists(file_data):
                    # Use shutil to copy file
                    shutil.copy2(file_data, full_path)
                else:
                    raise StorageError(f"Source file not found: {file_data}")
            else:
                # Assume it's a file-like object
                async with aiofiles.open(full_path, 'wb') as f:
                    while True:
                        chunk = file_data.read(8192)
                        if not chunk:
                            break
                        await f.write(chunk)
            
            # Store metadata if provided
            if metadata:
                metadata_path = f"{full_path}.metadata"
                async with aiofiles.open(metadata_path, 'w') as f:
                    await f.write(str(metadata))
            
            logger.debug(f"Stored file at {full_path}")
            return file_path
            
        except Exception as e:
            error_msg = f"Error storing file at {full_path}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    async def get_file(self, file_path: str) -> Tuple[bytes, Optional[Dict[str, str]]]:
        """
        Get a file from local storage.
        
        Args:
            file_path: The path to the file (relative to base_dir)
            
        Returns:
            Tuple of (file_data, metadata)
        """
        full_path = os.path.join(self.base_dir, file_path)
        
        try:
            # Check if file exists
            if not await aiofiles.os.path.exists(full_path):
                raise StorageError(f"File not found: {file_path}")
            
            # Read file data
            async with aiofiles.open(full_path, 'rb') as f:
                file_data = await f.read()
            
            # Read metadata if it exists
            metadata = None
            metadata_path = f"{full_path}.metadata"
            if await aiofiles.os.path.exists(metadata_path):
                async with aiofiles.open(metadata_path, 'r') as f:
                    metadata_str = await f.read()
                    metadata = eval(metadata_str)  # Convert string to dict
            
            return file_data, metadata
            
        except Exception as e:
            error_msg = f"Error getting file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    async def get_file_stream(self, file_path: str) -> Tuple[BinaryIO, Optional[Dict[str, str]]]:
        """
        Get a file as a stream from local storage.
        
        Args:
            file_path: The path to the file (relative to base_dir)
            
        Returns:
            Tuple of (file_stream, metadata)
        """
        # For local storage, just return a standard file object
        full_path = os.path.join(self.base_dir, file_path)
        
        try:
            # Check if file exists
            if not os.path.exists(full_path):
                raise StorageError(f"File not found: {file_path}")
            
            # Open file stream
            file_stream = open(full_path, 'rb')
            
            # Read metadata if it exists
            metadata = None
            metadata_path = f"{full_path}.metadata"
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata_str = f.read()
                    metadata = eval(metadata_str)  # Convert string to dict
            
            return file_stream, metadata
            
        except Exception as e:
            error_msg = f"Error getting file stream for {file_path}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from local storage.
        
        Args:
            file_path: The path to the file (relative to base_dir)
            
        Returns:
            True if the file was deleted, False otherwise
        """
        full_path = os.path.join(self.base_dir, file_path)
        
        try:
            # Check if file exists
            if not await aiofiles.os.path.exists(full_path):
                logger.warning(f"File not found for deletion: {file_path}")
                return False
            
            # Delete file
            await aiofiles.os.remove(full_path)
            
            # Delete metadata if it exists
            metadata_path = f"{full_path}.metadata"
            if await aiofiles.os.path.exists(metadata_path):
                await aiofiles.os.remove(metadata_path)
            
            logger.debug(f"Deleted file: {file_path}")
            return True
            
        except Exception as e:
            error_msg = f"Error deleting file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    async def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in local storage.
        
        Args:
            file_path: The path to the file (relative to base_dir)
            
        Returns:
            True if the file exists, False otherwise
        """
        full_path = os.path.join(self.base_dir, file_path)
        
        try:
            return await aiofiles.os.path.exists(full_path)
        except Exception as e:
            error_msg = f"Error checking if file exists {file_path}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    async def list_files(self, directory: str) -> List[Dict[str, Any]]:
        """
        List files in a directory in local storage.
        
        Args:
            directory: The directory to list files in (relative to base_dir)
            
        Returns:
            List of file information dictionaries
        """
        full_path = os.path.join(self.base_dir, directory)
        
        try:
            # Check if directory exists
            if not await aiofiles.os.path.exists(full_path) or not await aiofiles.os.path.isdir(full_path):
                raise StorageError(f"Directory not found: {directory}")
            
            files = []
            
            # List files in directory
            for file_name in os.listdir(full_path):
                file_path = os.path.join(full_path, file_name)
                
                # Skip metadata files and hidden files
                if file_name.endswith('.metadata') or file_name.startswith('.'):
                    continue
                
                # Skip directories
                if os.path.isdir(file_path):
                    continue
                
                # Get file stats
                stats = await aiofiles.os.stat(file_path)
                
                files.append({
                    'name': file_name,
                    'path': os.path.join(directory, file_name),
                    'size': stats.st_size,
                    'modified': datetime.fromtimestamp(stats.st_mtime).isoformat(),
                    'created': datetime.fromtimestamp(stats.st_ctime).isoformat()
                })
            
            return files
            
        except Exception as e:
            error_msg = f"Error listing files in {directory}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    async def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Get a URL for a file in local storage.
        
        Note: For local storage, this returns a file:// URL. In a real application,
        you would likely want to serve these files through your web server.
        
        Args:
            file_path: The path to the file (relative to base_dir)
            expires_in: Time in seconds until the URL expires (ignored for local storage)
            
        Returns:
            A URL for accessing the file
        """
        full_path = os.path.join(self.base_dir, file_path)
        
        try:
            # Check if file exists
            if not await aiofiles.os.path.exists(full_path):
                raise StorageError(f"File not found: {file_path}")
            
            # For local storage, just return a file:// URL
            return f"file://{os.path.abspath(full_path)}"
            
        except Exception as e:
            error_msg = f"Error getting file URL for {file_path}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e


class S3StorageService(StorageService):
    """Storage service that stores files in Amazon S3."""
    
    def __init__(self, bucket_name: str, aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None, region_name: Optional[str] = None,
                 endpoint_url: Optional[str] = None):
        """
        Initialize the S3 storage service.
        
        Args:
            bucket_name: The name of the S3 bucket
            aws_access_key_id: AWS access key ID (optional, can be read from environment)
            aws_secret_access_key: AWS secret access key (optional, can be read from environment)
            region_name: AWS region name (optional, can be read from environment)
            endpoint_url: Custom endpoint URL for S3-compatible services
        """
        self.bucket_name = bucket_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.endpoint_url = endpoint_url
        self.s3_client = None
    
    async def initialize(self):
        """Initialize the storage service."""
        # Create S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name,
                endpoint_url=self.endpoint_url
            )
            
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            
            logger.info(f"Initialized S3 storage service with bucket: {self.bucket_name}")
            
        except ClientError as e:
            error_msg = f"Error initializing S3 storage service: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    async def store_file(
        self, 
        file_data: Union[bytes, BinaryIO, str], 
        file_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Store a file in S3.
        
        Args:
            file_data: The file data (bytes, file-like object, or path)
            file_path: The path (key) to store the file at in S3
            content_type: The MIME type of the file
            metadata: Additional metadata to store with the file
            
        Returns:
            The path where the file was stored
        """
        if not self.s3_client:
            await self.initialize()
        
        # Detect content type if not provided
        if not content_type and isinstance(file_path, str):
            content_type, _ = mimetypes.guess_type(file_path)
        
        # Convert metadata values to strings
        if metadata:
            metadata = {k: str(v) for k, v in metadata.items()}
        
        extra_args = {
            'ContentType': content_type,
            'Metadata': metadata or {}
        }
        
        try:
            # Handle different input types
            if isinstance(file_data, bytes):
                await asyncio.to_thread(
                    self.s3_client.put_object,
                    Bucket=self.bucket_name,
                    Key=file_path,
                    Body=file_data,
                    **extra_args
                )
            elif isinstance(file_data, str):
                # Assume it's a path
                await asyncio.to_thread(
                    self.s3_client.upload_file,
                    file_data,
                    self.bucket_name,
                    file_path,
                    ExtraArgs=extra_args
                )
            else:
                # Assume it's a file-like object
                await asyncio.to_thread(
                    self.s3_client.upload_fileobj,
                    file_data,
                    self.bucket_name,
                    file_path,
                    ExtraArgs=extra_args
                )
            
            logger.debug(f"Stored file in S3 at {file_path}")
            return file_path
            
        except ClientError as e:
            error_msg = f"Error storing file in S3 at {file_path}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    async def get_file(self, file_path: str) -> Tuple[bytes, Optional[Dict[str, str]]]:
        """
        Get a file from S3.
        
        Args:
            file_path: The path (key) to the file in S3
            
        Returns:
            Tuple of (file_data, metadata)
        """
        if not self.s3_client:
            await self.initialize()
        
        try:
            # Get object
            response = await asyncio.to_thread(
                self.s3_client.get_object,
                Bucket=self.bucket_name,
                Key=file_path
            )
            
            # Read file data
            file_data = await asyncio.to_thread(response['Body'].read)
            
            # Extract metadata
            metadata = response.get('Metadata')
            
            return file_data, metadata
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise StorageError(f"File not found in S3: {file_path}")
            error_msg = f"Error getting file from S3 {file_path}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            file_path: The path (key) to the file in S3
            
        Returns:
            True if the file was deleted, False otherwise
        """
        if not self.s3_client:
            await self.initialize()
        
        try:
            # Delete object
            await asyncio.to_thread(
                self.s3_client.delete_object,
                Bucket=self.bucket_name,
                Key=file_path
            )
            
            logger.debug(f"Deleted file from S3: {file_path}")
            return True
            
        except ClientError as e:
            error_msg = f"Error deleting file from S3 {file_path}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    async def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            file_path: The path (key) to the file in S3
            
        Returns:
            True if the file exists, False otherwise
        """
        if not self.s3_client:
            await self.initialize()
        
        try:
            # Check if object exists
            await asyncio.to_thread(
                self.s3_client.head_object,
                Bucket=self.bucket_name,
                Key=file_path
            )
            
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            error_msg = f"Error checking if file exists in S3 {file_path}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    async def list_files(self, directory: str) -> List[Dict[str, Any]]:
        """
        List files in a directory in S3.
        
        Args:
            directory: The directory (prefix) to list files in
            
        Returns:
            List of file information dictionaries
        """
        if not self.s3_client:
            await self.initialize()
        
        # Ensure directory ends with a slash if not empty
        if directory and not directory.endswith('/'):
            directory += '/'
        
        try:
            # List objects with the given prefix
            response = await asyncio.to_thread(
                self.s3_client.list_objects_v2,
                Bucket=self.bucket_name,
                Prefix=directory,
                Delimiter='/'
            )
            
            files = []
            
            # Process files (objects)
            for obj in response.get('Contents', []):
                # Skip directories themselves
                if obj['Key'] == directory:
                    continue
                
                files.append({
                    'name': os.path.basename(obj['Key']),
                    'path': obj['Key'],
                    'size': obj['Size'],
                    'modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag'].strip('"')
                })
            
            return files
            
        except ClientError as e:
            error_msg = f"Error listing files in S3 {directory}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    async def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Get a pre-signed URL for a file in S3.
        
        Args:
            file_path: The path (key) to the file in S3
            expires_in: Time in seconds until the URL expires
            
        Returns:
            A pre-signed URL for accessing the file
        """
        if not self.s3_client:
            await self.initialize()
        
        try:
            # Generate pre-signed URL
            url = await asyncio.to_thread(
                self.s3_client.generate_presigned_url,
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_path},
                ExpiresIn=expires_in
            )
            
            return url
            
        except ClientError as e:
            error_msg = f"Error generating pre-signed URL for S3 {file_path}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e


# Factory function to create the appropriate storage service
def get_storage_service() -> StorageService:
    """
    Get the appropriate storage service based on configuration.
    
    Returns:
        A storage service instance
    """
    storage_type = settings.storage_type.lower()
    
    if storage_type == 'local':
        return LocalStorageService(settings.storage_path)
    
    elif storage_type == 's3':
        return S3StorageService(
            bucket_name=settings.s3_bucket_name,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
            endpoint_url=settings.s3_endpoint_url
        )
    
    elif storage_type == 'azure':
        # Azure Blob Storage implementation would go here
        raise NotImplementedError("Azure Blob Storage not implemented yet")
    
    elif storage_type == 'gcp':
        # Google Cloud Storage implementation would go here
        raise NotImplementedError("Google Cloud Storage not implemented yet")
    
    else:
        logger.warning(f"Unknown storage type '{storage_type}', falling back to local storage")
        return LocalStorageService(settings.storage_path)


# Helper function to generate a unique file path for uploads
def generate_unique_path(original_filename: str, prefix: Optional[str] = None) -> str:
    """
    Generate a unique path for uploading a file.
    
    Args:
        original_filename: The original filename
        prefix: Optional prefix for the path
        
    Returns:
        A unique path
    """
    # Extract extension
    _, ext = os.path.splitext(original_filename)
    
    # Generate UUID
    unique_id = str(uuid.uuid4())
    
    # Create path
    if prefix:
        if not prefix.endswith('/'):
            prefix += '/'
        return f"{prefix}{unique_id}{ext}"
    else:
        # Use current date as prefix
        date_prefix = datetime.now().strftime('%Y/%m/%d')
        return f"{date_prefix}/{unique_id}{ext}"