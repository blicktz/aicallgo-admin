"""
Recording service for managing call recordings with B2 presigned URLs.
Uses direct database access and boto3 for S3-compatible B2 storage.
"""
import os
from typing import Optional
from datetime import datetime
import logging

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import settings
from database.models import Recording

logger = logging.getLogger(__name__)


class RecordingService:
    """Service for accessing call recordings from B2 storage."""

    def __init__(self):
        """Initialize recording service with B2 configuration."""
        # B2 Configuration from Pydantic settings
        self.b2_key_id = settings.B2_APPLICATION_KEY_ID
        self.b2_key = settings.B2_APPLICATION_KEY
        self.b2_bucket = settings.B2_BUCKET_NAME
        self.b2_region = settings.B2_REGION

        # Derive B2 endpoint from region (unless explicitly overridden)
        # Pattern: https://s3.{region}.backblazeb2.com
        self.b2_endpoint = os.getenv(
            "B2_ENDPOINT_URL",
            f"https://s3.{self.b2_region}.backblazeb2.com"
        )

        # URL expiration time (1 hour by default)
        self.url_expiration_seconds = int(
            os.getenv("RECORDING_URL_EXPIRATION_SECONDS", "3600")
        )

    def _get_b2_client(self):
        """
        Get configured B2 client using S3-compatible API.

        Returns:
            boto3 S3 client configured for B2

        Raises:
            ValueError: If B2 credentials are not configured
        """
        if not self.b2_key_id or not self.b2_key:
            raise ValueError(
                "B2 credentials not configured. Set B2_APPLICATION_KEY_ID and "
                "B2_APPLICATION_KEY environment variables."
            )

        # Configure boto3 with checksum workaround for B2 compatibility
        # Required for boto3 >= 1.35.99 due to unsupported checksum headers in B2
        boto_config = Config(
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            signature_version="s3v4",
            region_name=self.b2_region,
        )

        return boto3.client(
            "s3",
            endpoint_url=self.b2_endpoint,
            aws_access_key_id=self.b2_key_id,
            aws_secret_access_key=self.b2_key,
            config=boto_config,
        )

    def _extract_b2_key_from_url(self, internal_recording_url: str) -> str:
        """
        Extract B2 object key from internal recording URL.

        Args:
            internal_recording_url: B2 URL like
                https://aicallgo.s3.us-west-004.backblazeb2.com/recordings/2025/10/RExxxx.mp3

        Returns:
            B2 object key like recordings/2025/10/RExxxx.mp3

        Raises:
            ValueError: If URL format is invalid
        """
        try:
            # Parse URL to extract the key part after bucket name
            # Format: https://bucket.s3.region.backblazeb2.com/key/path
            url_parts = internal_recording_url.split("/")

            # Find where the key starts (after the domain)
            if len(url_parts) >= 4:
                # Join everything after the domain (index 3 and beyond)
                key = "/".join(url_parts[3:])

                # Remove query parameters if present
                key = key.split("?")[0]

                logger.debug(
                    f"Extracted B2 key: {key} from URL: {internal_recording_url}"
                )
                return key
            else:
                raise ValueError(
                    f"Invalid internal recording URL format: {internal_recording_url}"
                )

        except Exception as e:
            logger.error(
                f"Failed to extract B2 key from URL {internal_recording_url}: {e}"
            )
            raise ValueError(f"Invalid internal recording URL: {e}")

    def get_recording_by_call_sid(
        self, session: Session, call_sid: str
    ) -> Optional[Recording]:
        """
        Get recording record by Twilio call SID.

        Args:
            session: Database session
            call_sid: Twilio call SID

        Returns:
            Recording object or None if not found
        """
        try:
            query = select(Recording).where(Recording.call_sid == call_sid)
            result = session.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error fetching recording for call SID {call_sid}: {e}")
            raise

    def generate_presigned_url(
        self, internal_recording_url: str, expiration: Optional[int] = None
    ) -> dict:
        """
        Generate presigned URL for recording playback.

        Args:
            internal_recording_url: B2 URL to the recording
            expiration: URL expiration in seconds (default: 1 hour)

        Returns:
            Dict with:
            - url: Presigned URL for playback
            - expires_at: Expiration timestamp
            - content_type: Audio MIME type

        Raises:
            ValueError: If URL is invalid or B2 credentials missing
            ClientError: If B2 API call fails
        """
        if not internal_recording_url:
            raise ValueError("Recording URL is empty")

        expiration = expiration or self.url_expiration_seconds

        try:
            # Extract B2 key from URL
            b2_key = self._extract_b2_key_from_url(internal_recording_url)

            # Get B2 client
            b2_client = self._get_b2_client()

            # Generate presigned URL
            presigned_url = b2_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.b2_bucket, "Key": b2_key},
                ExpiresIn=expiration,
            )

            # Calculate expiration timestamp
            expires_at = datetime.utcnow()
            from datetime import timedelta
            expires_at = expires_at + timedelta(seconds=expiration)

            # Determine content type from file extension
            content_type = self._get_content_type(internal_recording_url)

            logger.info(
                f"Generated presigned URL for {b2_key}, expires at {expires_at}"
            )

            return {
                "url": presigned_url,
                "expires_at": expires_at.isoformat() + "Z",
                "content_type": content_type,
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            logger.error(f"B2 ClientError while generating presigned URL: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise

    def _get_content_type(self, file_url: str) -> str:
        """
        Determine content type based on file extension.

        Args:
            file_url: URL of the file

        Returns:
            MIME type for the audio file
        """
        # Remove query parameters if present
        clean_url = file_url.split("?")[0].lower()

        if clean_url.endswith(".mp3"):
            return "audio/mpeg"
        elif clean_url.endswith(".wav"):
            return "audio/wav"
        elif clean_url.endswith(".m4a"):
            return "audio/mp4"
        else:
            # Default to mp3 if extension is unclear
            return "audio/mpeg"

    def generate_download_url(
        self, internal_recording_url: str, call_sid: str, expiration: Optional[int] = None
    ) -> dict:
        """
        Generate presigned URL for recording download with attachment disposition.

        Args:
            internal_recording_url: B2 URL to the recording
            call_sid: Twilio call SID for filename
            expiration: URL expiration in seconds (default: 1 hour)

        Returns:
            Dict with:
            - url: Presigned URL for download
            - expires_at: Expiration timestamp
            - filename: Suggested filename

        Raises:
            ValueError: If URL is invalid or B2 credentials missing
            ClientError: If B2 API call fails
        """
        if not internal_recording_url:
            raise ValueError("Recording URL is empty")

        expiration = expiration or self.url_expiration_seconds

        try:
            # Extract B2 key from URL
            b2_key = self._extract_b2_key_from_url(internal_recording_url)

            # Get B2 client
            b2_client = self._get_b2_client()

            # Determine file extension
            file_extension = "mp3" if b2_key.endswith(".mp3") else "wav"
            filename = f"recording-{call_sid}.{file_extension}"

            # Generate presigned URL with download disposition
            presigned_url = b2_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.b2_bucket,
                    "Key": b2_key,
                    "ResponseContentDisposition": f'attachment; filename="{filename}"'
                },
                ExpiresIn=expiration,
            )

            # Calculate expiration timestamp
            expires_at = datetime.utcnow()
            from datetime import timedelta
            expires_at = expires_at + timedelta(seconds=expiration)

            logger.info(
                f"Generated download URL for {b2_key}, expires at {expires_at}"
            )

            return {
                "url": presigned_url,
                "expires_at": expires_at.isoformat() + "Z",
                "filename": filename,
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            logger.error(f"B2 ClientError while generating download URL: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Error generating download URL: {e}")
            raise

    def get_recording_playback_info(
        self, session: Session, call_sid: str
    ) -> Optional[dict]:
        """
        Get recording playback information including presigned URL.

        This is the main method to use for displaying recordings in UI.

        Args:
            session: Database session
            call_sid: Twilio call SID

        Returns:
            Dict with recording info and presigned URL, or None if no recording
            {
                "recording_sid": str,
                "url": str,  # Presigned URL for playback
                "expires_at": str,  # ISO timestamp
                "content_type": str,  # MIME type
                "duration_seconds": int,
                "status": str
            }

        Raises:
            ValueError: If configuration is invalid
            ClientError: If B2 API call fails
        """
        try:
            # Get recording from database
            recording = self.get_recording_by_call_sid(session, call_sid)

            if not recording:
                logger.debug(f"No recording found for call SID: {call_sid}")
                return None

            # Check if recording is completed
            if recording.recording_status != "completed":
                logger.debug(
                    f"Recording {recording.recording_sid} status is "
                    f"{recording.recording_status}, not ready for playback"
                )
                return None

            # Check if internal URL exists
            if not recording.internal_recording_url:
                logger.warning(
                    f"Recording {recording.recording_sid} has no internal URL, "
                    "may not have been uploaded to B2 yet"
                )
                return None

            # Generate presigned URL
            presigned_info = self.generate_presigned_url(
                recording.internal_recording_url
            )

            # Return complete recording info
            return {
                "recording_sid": recording.recording_sid,
                "url": presigned_info["url"],
                "expires_at": presigned_info["expires_at"],
                "content_type": presigned_info["content_type"],
                "duration_seconds": recording.recording_duration_seconds,
                "status": recording.recording_status,
            }

        except Exception as e:
            logger.error(
                f"Error getting recording playback info for call {call_sid}: {e}"
            )
            raise


# Singleton instance
_recording_service = None


def get_recording_service() -> RecordingService:
    """
    Get or create singleton recording service instance.

    Returns:
        RecordingService instance
    """
    global _recording_service
    if _recording_service is None:
        _recording_service = RecordingService()
    return _recording_service
