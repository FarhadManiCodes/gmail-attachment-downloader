"""
Gmail API client for authentication and email operations.

This module provides a comprehensive Gmail API client that demonstrates:
- OAuth2 authentication flow with Google APIs
- Async programming with proper error handling
- Rate limiting and exponential backoff
- API quota management and monitoring
- Structured error handling with custom exceptions
- Real-time email monitoring capabilities
- Integration with configuration system

This implementation follows Google's best practices for Gmail API usage,
including proper authentication, rate limiting, and error handling patterns.
"""

import asyncio
import base64
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncIterator, Tuple

import backoff
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

# Import our helper functions - ALWAYS use these instead of reimplementing
from .config import AppConfig, load_config
from .utils import (
    is_valid_email,
    extract_email_address,
    parse_date,
    sanitize_filename,
    format_file_size,
    ensure_directory,
)


# Custom exceptions for Gmail operations
class GmailError(Exception):
    """Base exception for Gmail client operations."""
    pass


class GmailAuthenticationError(GmailError):
    """Raised when Gmail authentication fails."""
    pass


class GmailRateLimitError(GmailError):
    """Raised when Gmail API rate limits are exceeded."""
    
    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(
            f"Gmail API rate limit exceeded. Retry after {retry_after} seconds"
        )


class GmailQuotaExceededError(GmailError):
    """Raised when Gmail API quota is exceeded."""
    pass


class GmailAttachmentError(GmailError):
    """Raised when attachment operations fail."""
    pass


# Data classes for structured data
from dataclasses import dataclass


@dataclass
class EmailMessage:
    """Represents a Gmail message with metadata."""
    
    message_id: str
    thread_id: str
    sender: str
    recipient: str
    subject: str
    date: datetime
    snippet: str
    has_attachments: bool
    attachment_count: int = 0
    raw_message: Optional[Dict[str, Any]] = None


@dataclass
class EmailAttachment:
    """Represents a Gmail attachment."""
    
    attachment_id: str
    message_id: str
    filename: str
    mime_type: str
    size: int
    
    @property
    def extension(self) -> str:
        """Get file extension from filename."""
        return Path(self.filename).suffix.lower()
    
    @property
    def safe_filename(self) -> str:
        """Get sanitized filename - ALWAYS use utils.sanitize_filename()."""
        return sanitize_filename(self.filename)
    
    @property
    def size_display(self) -> str:
        """Get human-readable size - ALWAYS use utils.format_file_size()."""
        return format_file_size(self.size)


class GmailClient:
    """
    Gmail API client with OAuth authentication and robust error handling.
    
    This client implements Google's best practices including:
    - Proper OAuth2 authentication flow
    - Exponential backoff for rate limiting
    - Quota monitoring and management
    - Async operations with semaphore control
    - Comprehensive error handling
    - Real-time message monitoring
    """
    
    # Gmail API scopes - readonly is sufficient for our use case
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    
    def __init__(self, config_path: Optional[str] = None, config: Optional[AppConfig] = None):
        """
        Initialize Gmail client with configuration.
        
        Args:
            config_path: Path to configuration file (optional)
            config: Configuration object (optional, takes precedence over config_path)
        """
        if config:
            self.config = config
        else:
            self.config = load_config(config_path)
        
        self.gmail_config = self.config.gmail
        self.logger = logging.getLogger(__name__)
        
        # API service and credentials
        self.service = None
        self.credentials = None
        
        # Rate limiting control
        self._semaphore = asyncio.Semaphore(
            self.config.gmail.requests_per_minute // 60
        )  # Per second limit
        self._quota_used = 0
        self._quota_reset_time = datetime.now() + timedelta(days=1)
        
        # Statistics tracking
        self.stats = {
            "requests_made": 0,
            "quota_units_used": 0,
            "rate_limit_hits": 0,
            "authentication_refreshes": 0,
        }
        
        self.logger.info("Gmail client initialized")
    
    async def authenticate(self) -> None:
        """
        Handle OAuth2 authentication with Google Gmail API.
        
        This method implements the complete OAuth2 flow:
        1. Check for existing valid credentials
        2. Refresh expired credentials if possible
        3. Perform initial authentication flow if needed
        4. Save credentials for future use
        
        Raises:
            GmailAuthenticationError: If authentication fails
        """
        try:
            credentials_path = Path(self.gmail_config.credentials_file)
            token_path = Path(self.gmail_config.token_file)
            
            # Ensure credentials file exists
            if not credentials_path.exists():
                raise GmailAuthenticationError(
                    f"Credentials file not found: {credentials_path}\n"
                    f"Please download OAuth2 credentials from Google Cloud Console"
                )
            
            # Ensure the token directory exists - ALWAYS use utils.ensure_directory()
            ensure_directory(token_path.parent)
            
            credentials = None
            
            # Load existing token if available
            if token_path.exists():
                try:
                    credentials = Credentials.from_authorized_user_file(
                        str(token_path), self.SCOPES
                    )
                    self.logger.info("Loaded existing credentials from token file")
                except Exception as e:
                    self.logger.warning(f"Failed to load existing credentials: {e}")
            
            # Refresh or obtain new credentials
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    try:
                        self.logger.info("Refreshing expired credentials")
                        credentials.refresh(Request())
                        self.stats["authentication_refreshes"] += 1
                        self.logger.info("Successfully refreshed credentials")
                    except RefreshError as e:
                        self.logger.error(f"Token refresh failed: {e}")
                        raise GmailAuthenticationError(f"Token refresh failed: {e}")
                
                # Perform initial authentication flow
                if not credentials:
                    self.logger.info("Starting OAuth2 authentication flow")
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(credentials_path), self.SCOPES
                        )
                        # Run local server for OAuth callback
                        credentials = flow.run_local_server(port=0)
                        self.logger.info("OAuth2 authentication completed successfully")
                    except Exception as e:
                        self.logger.error(f"OAuth2 flow failed: {e}")
                        raise GmailAuthenticationError(f"OAuth2 flow failed: {e}")
                
                # Save credentials for future use
                try:
                    with open(token_path, "w") as token_file:
                        token_file.write(credentials.to_json())
                    self.logger.info(f"Saved credentials to {token_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to save credentials: {e}")
            
            # Build Gmail service
            self.credentials = credentials
            self.service = build("gmail", "v1", credentials=credentials)
            self.logger.info("Gmail API service initialized successfully")
            
        except GmailAuthenticationError:
            raise  # Re-raise our custom errors
        except Exception as e:
            raise GmailAuthenticationError(f"Gmail authentication failed: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated and ready to use."""
        return self.service is not None and self.credentials is not None
    
    @backoff.on_exception(
        backoff.expo,
        (HttpError, GmailRateLimitError),
        max_tries=5,
        jitter=backoff.full_jitter,
        max_time=300,  # 5 minutes maximum
    )
    async def _make_api_request(self, request_func, quota_units: int = 1) -> Any:
        """
        Make a Gmail API request with rate limiting and error handling.
        
        This method implements:
        - Semaphore-based concurrency control
        - Quota monitoring and management
        - Exponential backoff for rate limiting
        - Proper error handling and logging
        
        Args:
            request_func: Function that makes the actual API request
            quota_units: Number of quota units this request consumes
            
        Returns:
            API response data
            
        Raises:
            GmailRateLimitError: If rate limits are exceeded
            GmailQuotaExceededError: If daily quota is exceeded
            GmailError: For other API errors
        """
        async with self._semaphore:
            try:
                # Check quota limits
                if self._quota_used + quota_units > self.gmail_config.requests_per_day:
                    raise GmailQuotaExceededError(
                        f"Daily quota exceeded: {self._quota_used} + {quota_units} > {self.gmail_config.requests_per_day}"
                    )
                
                # Execute the request (run in thread pool to avoid blocking)
                response = await asyncio.to_thread(request_func)
                
                # Update statistics
                self.stats["requests_made"] += 1
                self.stats["quota_units_used"] += quota_units
                self._quota_used += quota_units
                
                # Reset daily quota counter if needed
                if datetime.now() >= self._quota_reset_time:
                    self._quota_used = 0
                    self._quota_reset_time = datetime.now() + timedelta(days=1)
                    self.logger.info("Daily quota counter reset")
                
                return response
                
            except HttpError as e:
                error_details = e.error_details[0] if e.error_details else {}
                error_reason = error_details.get("reason", "")
                
                if e.resp.status == 429 or error_reason in [
                    "rateLimitExceeded",
                    "userRateLimitExceeded",
                ]:
                    self.stats["rate_limit_hits"] += 1
                    retry_after = int(e.resp.get("retry-after", 60))
                    self.logger.warning(
                        f"Rate limit hit, backing off for {retry_after} seconds"
                    )
                    raise GmailRateLimitError(retry_after)
                
                elif e.resp.status == 403 and error_reason == "quotaExceeded":
                    raise GmailQuotaExceededError("Daily API quota exceeded")
                
                elif e.resp.status == 401:
                    # Try to refresh credentials once
                    try:
                        await self.authenticate()
                        self.logger.info(
                            "Re-authenticated successfully, retrying request"
                        )
                        return await asyncio.to_thread(request_func)
                    except Exception as auth_error:
                        raise GmailAuthenticationError(
                            f"Re-authentication failed: {auth_error}"
                        )
                
                else:
                    self.logger.error(f"Gmail API error: {e}")
                    raise GmailError(f"Gmail API request failed: {e}")
    
    def build_search_query(
        self,
        senders: Optional[List[str]] = None,
        after_date: Optional[str] = None,
        before_date: Optional[str] = None,
        has_attachment: bool = True,
        subject_keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None,
        extensions: Optional[List[str]] = None,
    ) -> str:
        """
        Build Gmail search query from filter parameters.
        
        This method demonstrates proper Gmail query syntax and uses our
        helper functions for validation and date parsing.
        
        Args:
            senders: List of sender email addresses
            after_date: Search for emails after this date (YYYY-MM-DD format)
            before_date: Search for emails before this date (YYYY-MM-DD format)
            has_attachment: Whether to include only emails with attachments
            subject_keywords: Keywords that must appear in subject
            exclude_keywords: Keywords to exclude from results
            extensions: File extensions to search for (e.g., ['.pdf', '.xlsx'])
            
        Returns:
            Gmail search query string
        """
        query_parts = []
        
        # Add sender filters - ALWAYS use utils.is_valid_email()
        if senders:
            valid_senders = []
            for sender in senders:
                clean_email = extract_email_address(sender)
                if is_valid_email(clean_email):
                    valid_senders.append(clean_email)
                else:
                    self.logger.warning(f"Skipping invalid sender email: {sender}")
            
            if valid_senders:
                if len(valid_senders) == 1:
                    query_parts.append(f"from:{valid_senders[0]}")
                else:
                    sender_query = " OR ".join(
                        [f"from:{email}" for email in valid_senders]
                    )
                    query_parts.append(f"({sender_query})")
        
        # Add date filters - ALWAYS use utils.parse_date()
        if after_date:
            parsed_date = parse_date(after_date)
            if parsed_date:
                query_parts.append(f"after:{parsed_date.strftime('%Y/%m/%d')}")
            else:
                self.logger.warning(f"Invalid after_date format: {after_date}")
        
        if before_date:
            parsed_date = parse_date(before_date)
            if parsed_date:
                query_parts.append(f"before:{parsed_date.strftime('%Y/%m/%d')}")
            else:
                self.logger.warning(f"Invalid before_date format: {before_date}")
        
        # Add attachment filter
        if has_attachment:
            query_parts.append("has:attachment")
        
        # Add file extension filter
        if extensions:
            extension_queries = []
            for ext in extensions:
                # Remove leading dot if present
                clean_ext = ext.lstrip(".")
                extension_queries.append(f"filename:{clean_ext}")
            
            if extension_queries:
                if len(extension_queries) == 1:
                    query_parts.append(extension_queries[0])
                else:
                    query_parts.append(f"({' OR '.join(extension_queries)})")
        
        # Add subject keyword filters
        if subject_keywords:
            for keyword in subject_keywords:
                query_parts.append(f'subject:"{keyword}"')
        
        # Add exclusion filters
        if exclude_keywords:
            for keyword in exclude_keywords:
                query_parts.append(f"-{keyword}")
        
        query = " ".join(query_parts)
        self.logger.debug(f"Built search query: {query}")
        return query
    
    async def search_messages(
        self, query: str, max_results: Optional[int] = None
    ) -> AsyncIterator[str]:
        """
        Search for messages using Gmail query syntax.
        
        This method handles:
        - Pagination for large result sets
        - Proper quota management (1 unit per request)
        - Async iteration for memory efficiency
        
        Args:
            query: Gmail search query (e.g., "from:sender@example.com has:attachment")
            max_results: Maximum number of messages to return (None = all)
            
        Yields:
            Message IDs that match the search criteria
        """
        if not self.is_authenticated():
            raise GmailError("Client not authenticated. Call authenticate() first.")
        
        self.logger.info(f"Searching messages with query: {query}")
        
        page_token = None
        results_returned = 0
        
        while True:
            # Build request parameters
            request_params = {
                "userId": "me",
                "q": query,
                "maxResults": (
                    min(500, max_results - results_returned) if max_results else 500
                ),
            }
            
            if page_token:
                request_params["pageToken"] = page_token
            
            # Make the API request - costs 1 quota unit
            def make_request():
                return self.service.users().messages().list(**request_params).execute()
            
            try:
                response = await self._make_api_request(make_request, quota_units=1)
                
                # Yield message IDs
                messages = response.get("messages", [])
                for message in messages:
                    yield message["id"]
                    results_returned += 1
                    
                    if max_results and results_returned >= max_results:
                        return
                
                # Check for more pages
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
                
                self.logger.debug(
                    f"Retrieved {len(messages)} messages, continuing with pagination"
                )
                
            except Exception as e:
                self.logger.error(f"Error searching messages: {e}")
                raise
        
        self.logger.info(f"Search completed: {results_returned} messages found")
    
    async def get_message_details(
        self, message_id: str, include_body: bool = False
    ) -> EmailMessage:
        """
        Get detailed information about a specific message.
        
        Args:
            message_id: Gmail message ID
            include_body: Whether to include full message body (costs more quota)
            
        Returns:
            EmailMessage object with parsed message details
            
        Raises:
            GmailError: If message cannot be retrieved
        """
        if not self.is_authenticated():
            raise GmailError("Client not authenticated. Call authenticate() first.")
        
        try:
            # Choose format based on whether we need the body
            # 'metadata' is lighter weight (1 quota unit) vs 'full' (5 quota units)
            format_type = "full" if include_body else "metadata"
            quota_cost = 5 if include_body else 1
            
            def make_request():
                return (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=message_id, format=format_type)
                    .execute()
                )
            
            message_data = await self._make_api_request(
                make_request, quota_units=quota_cost
            )
            
            # Parse message headers
            headers = {}
            payload = message_data.get("payload", {})
            for header in payload.get("headers", []):
                headers[header["name"].lower()] = header["value"]
            
            # Extract and validate sender email - ALWAYS use utils functions
            sender_raw = headers.get("from", "Unknown")
            sender = extract_email_address(sender_raw)
            if not is_valid_email(sender):
                self.logger.warning(f"Invalid sender email format: {sender_raw}")
                sender = sender_raw  # Keep original if validation fails
            
            # Extract other email details
            recipient = extract_email_address(headers.get("to", ""))
            subject = headers.get("subject", "No Subject")
            
            # Parse date - ALWAYS use utils.parse_date()
            date_str = headers.get("date", "")
            message_date = parse_date(date_str) if date_str else None
            
            if not message_date:
                # Fallback to internal date if header parsing fails
                internal_date = message_data.get("internalDate")
                if internal_date:
                    try:
                        timestamp = int(internal_date) / 1000
                        message_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    except (ValueError, TypeError):
                        message_date = datetime.now(tz=timezone.utc)
                else:
                    message_date = datetime.now(tz=timezone.utc)
            
            # Check for attachments
            attachments = self._find_attachments(payload)
            
            return EmailMessage(
                message_id=message_id,
                thread_id=message_data.get("threadId", ""),
                sender=sender,
                recipient=recipient,
                subject=subject,
                date=message_date,
                snippet=message_data.get("snippet", ""),
                has_attachments=len(attachments) > 0,
                attachment_count=len(attachments),
                raw_message=message_data if include_body else None,
            )
            
        except Exception as e:
            self.logger.error(f"Error getting message details for {message_id}: {e}")
            raise GmailError(f"Failed to get message details: {e}")
    
    def _find_attachments(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Recursively find all attachments in a message payload.
        
        Gmail messages can have complex nested structures, so we need to
        recursively search through all parts to find attachments.
        
        Args:
            payload: Message payload from Gmail API
            
        Returns:
            List of attachment parts
        """
        attachments = []
        
        # Check if this part is an attachment
        body = payload.get("body", {})
        if body.get("attachmentId") and payload.get("filename"):
            attachments.append(payload)
        
        # Recursively check all parts
        for part in payload.get("parts", []):
            attachments.extend(self._find_attachments(part))
        
        return attachments
    
    async def get_message_attachments(self, message_id: str) -> List[EmailAttachment]:
        """
        Get all attachments for a specific message.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            List of EmailAttachment objects
            
        Raises:
            GmailError: If attachments cannot be retrieved
        """
        if not self.is_authenticated():
            raise GmailError("Client not authenticated. Call authenticate() first.")
        
        try:
            # Get full message to access attachment metadata
            def make_request():
                return (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=message_id, format="full")
                    .execute()
                )
            
            message_data = await self._make_api_request(make_request, quota_units=5)
            payload = message_data.get("payload", {})
            
            # Find all attachment parts
            attachment_parts = self._find_attachments(payload)
            attachments = []
            
            for part in attachment_parts:
                body = part.get("body", {})
                attachment_id = body.get("attachmentId")
                
                if attachment_id:
                    filename = part.get("filename", "attachment")
                    mime_type = part.get("mimeType", "application/octet-stream")
                    size = body.get("size", 0)
                    
                    # Create attachment object
                    attachment = EmailAttachment(
                        attachment_id=attachment_id,
                        message_id=message_id,
                        filename=filename,
                        mime_type=mime_type,
                        size=size,
                    )
                    
                    attachments.append(attachment)
                    self.logger.debug(
                        f"Found attachment: {attachment.safe_filename} ({attachment.size_display})"
                    )
            
            self.logger.info(
                f"Found {len(attachments)} attachments for message {message_id}"
            )
            return attachments
            
        except Exception as e:
            self.logger.error(
                f"Error getting attachments for message {message_id}: {e}"
            )
            raise GmailAttachmentError(f"Failed to get message attachments: {e}")
    
    async def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """
        Download attachment content from Gmail.
        
        Args:
            message_id: Gmail message ID
            attachment_id: Gmail attachment ID
            
        Returns:
            Raw attachment data as bytes
            
        Raises:
            GmailAttachmentError: If download fails
        """
        if not self.is_authenticated():
            raise GmailError("Client not authenticated. Call authenticate() first.")
        
        try:
            def make_request():
                return (
                    self.service.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=message_id, id=attachment_id)
                    .execute()
                )
            
            # Attachment downloads cost 10 quota units
            attachment_data = await self._make_api_request(make_request, quota_units=10)
            
            # Decode base64 data
            file_data = base64.urlsafe_b64decode(attachment_data["data"])
            
            self.logger.debug(
                f"Downloaded attachment {attachment_id}: {format_file_size(len(file_data))}"
            )
            return file_data
            
        except Exception as e:
            self.logger.error(f"Error downloading attachment {attachment_id}: {e}")
            raise GmailAttachmentError(f"Failed to download attachment: {e}")
    
    async def watch_for_new_messages(
        self, query: str, check_interval: Optional[int] = None
    ) -> AsyncIterator[str]:
        """
        Watch for new messages matching the query (async generator).
        
        This implements real-time monitoring by periodically checking for new messages.
        For production use, consider Gmail API push notifications for better efficiency.
        
        Args:
            query: Gmail search query to monitor
            check_interval: Check interval in seconds (uses config default if None)
            
        Yields:
            Message IDs of new messages as they arrive
        """
        if not self.is_authenticated():
            raise GmailError("Client not authenticated. Call authenticate() first.")
        
        interval = check_interval or self.config.watch.check_interval
        seen_message_ids = set()
        
        self.logger.info(f"Starting message monitoring (check interval: {interval}s)")
        
        # Initial scan to establish baseline
        try:
            initial_count = 0
            async for message_id in self.search_messages(query, max_results=100):
                seen_message_ids.add(message_id)
                initial_count += 1
            
            self.logger.info(f"Baseline established with {initial_count} messages")
        except Exception as e:
            self.logger.error(f"Failed to establish baseline: {e}")
            return
        
        while True:
            try:
                await asyncio.sleep(interval)
                
                # Search for current messages
                current_message_ids = set()
                async for message_id in self.search_messages(query, max_results=100):
                    current_message_ids.add(message_id)
                
                # Find new messages
                new_message_ids = current_message_ids - seen_message_ids
                
                if new_message_ids:
                    self.logger.info(f"Found {len(new_message_ids)} new messages")
                    
                    # Update seen set
                    seen_message_ids.update(new_message_ids)
                    
                    # Yield new messages (sorted by message ID for consistency)
                    for message_id in sorted(new_message_ids):
                        yield message_id
                
            except asyncio.CancelledError:
                self.logger.info("Message monitoring cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error during message monitoring: {e}")
                # Continue monitoring despite errors
                await asyncio.sleep(interval)
                continue
    
    def get_quota_status(self) -> Dict[str, Any]:
        """
        Get current quota usage and statistics.
        
        Returns:
            Dictionary with quota and usage information
        """
        return {
            "quota_used_today": self._quota_used,
            "quota_limit_daily": self.gmail_config.requests_per_day,
            "quota_remaining": self.gmail_config.requests_per_day - self._quota_used,
            "quota_reset_time": self._quota_reset_time.isoformat(),
            "statistics": self.stats.copy(),
        }
    
    async def get_user_profile(self) -> Dict[str, Any]:
        """
        Get the authenticated user's Gmail profile information.
        
        Returns:
            Dict containing user profile data including email address and message counts
            
        Raises:
            GmailError: If API call fails
        """
        if not self.is_authenticated():
            raise GmailError("Client not authenticated. Call authenticate() first.")
        
        try:
            def make_request():
                return self.service.users().getProfile(userId="me").execute()
            
            profile = await self._make_api_request(make_request, quota_units=1)
            self.logger.info(f"Retrieved profile for {profile.get('emailAddress', 'unknown')}")
            return profile
        except Exception as e:
            self.logger.error(f"Error getting user profile: {e}")
            raise GmailError(f"Failed to get user profile: {e}")
    
    async def test_connection(self) -> bool:
        """
        Test Gmail API connection and authentication.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            profile = await self.get_user_profile()
            email_address = profile.get("emailAddress", "Unknown")
            
            self.logger.info(f"Gmail connection test successful for: {email_address}")
            return True
            
        except Exception as e:
            self.logger.error(f"Gmail connection test failed: {e}")
            return False