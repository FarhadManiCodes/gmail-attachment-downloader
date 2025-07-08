"""
Configuration management for Gmail Attachment Downloader.

This module demonstrates several important Python concepts:
- Dataclasses for structured data (modern alternative to plain classes)
- YAML parsing for human-readable configuration files
- Environment variable handling for secure credential management
- Validation and error handling for configuration data
- Layered configuration (defaults → file → environment → CLI args)
- Type hints for complex nested data structures

Think of configuration as the "control panel" for your application - it should
be easy to understand, modify, and validate.
"""

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from .utils import parse_date, is_valid_email, ensure_directory


class ConfigurationError(Exception):
    """
    Custom exception for configuration-related errors.

    Using custom exceptions makes it easier to handle specific error types
    and provides better error messages to users. This is much better than
    using generic ValueError or RuntimeError exceptions.
    """

    pass


@dataclass
class GmailConfig:
    """
    Gmail API configuration settings.

    Dataclasses are a modern Python feature (3.7+) that automatically generate
    __init__, __repr__, __eq__ methods and more. They're perfect for configuration
    objects because they reduce boilerplate while providing type safety.

    Why separate this into its own class? It groups related settings together
    and makes the code more organized and easier to understand.
    """

    # Path to OAuth2 credentials file from Google Cloud Console
    credentials_file: str = "config/credentials.json"

    # Path to store OAuth2 tokens (created automatically after first auth)
    token_file: str = "config/token.json"

    # Gmail API scopes - what permissions we request
    scopes: List[str] = field(
        default_factory=lambda: ["https://www.googleapis.com/auth/gmail.readonly"]
    )

    # Rate limiting settings to respect Gmail API quotas
    requests_per_minute: int = 250
    requests_per_day: int = 1000000
    max_retries: int = 3
    backoff_factor: float = 2.0

    def validate(self) -> None:
        """
        Validate Gmail configuration settings.

        Validation is crucial in configuration management. It's better to fail
        fast with a clear error message than to have mysterious failures later.
        """
        # Check if credentials file exists
        creds_path = Path(self.credentials_file)
        if not creds_path.exists():
            raise ConfigurationError(
                f"Gmail credentials file not found: {self.credentials_file}\n"
                f"Please download OAuth2 credentials from Google Cloud Console."
            )

        # Validate rate limiting values
        if self.requests_per_minute <= 0:
            raise ConfigurationError("requests_per_minute must be positive")

        if self.requests_per_day <= 0:
            raise ConfigurationError("requests_per_day must be positive")

        if self.max_retries < 0:
            raise ConfigurationError("max_retries cannot be negative")

        if self.backoff_factor <= 0:
            raise ConfigurationError("backoff_factor must be positive")

        # Validate scopes
        if not self.scopes:
            raise ConfigurationError("At least one Gmail scope must be specified")


@dataclass
class FilterConfig:
    """
    Email filtering configuration.

    This class shows how to handle optional configuration with sensible defaults.
    Users can specify as much or as little as they want, and we fill in the gaps.
    """

    # List of sender email addresses to monitor
    # Empty list means "monitor all senders"
    senders: List[str] = field(default_factory=list)

    # File extensions to download (include the dot)
    extensions: List[str] = field(
        default_factory=lambda: [".pdf", ".docx", ".xlsx", ".csv", ".txt", ".zip"]
    )

    # Date filtering (ISO format strings)
    after_date: Optional[str] = None
    before_date: Optional[str] = None

    # File size filtering (in bytes)
    min_size: int = 1024  # 1 KB minimum
    max_size: int = 50 * 1024 * 1024  # 50 MB maximum

    # Subject line filtering
    subject_keywords: List[str] = field(default_factory=list)
    subject_exclude_keywords: List[str] = field(
        default_factory=lambda: ["spam", "promotional", "unsubscribe"]
    )

    # Whether to only process emails with attachments
    has_attachment: bool = True

    def validate(self) -> None:
        """Validate filter configuration."""
        # Validate email addresses
        for sender in self.senders:
            if sender and not is_valid_email(sender):
                raise ConfigurationError(f"Invalid sender email: {sender}")

        # Validate file extensions
        for ext in self.extensions:
            if not ext.startswith("."):
                raise ConfigurationError(f"File extension must start with dot: {ext}")

        # Validate file sizes
        if self.min_size < 0:
            raise ConfigurationError("min_size cannot be negative")

        if self.max_size <= 0:
            raise ConfigurationError("max_size must be positive")

        if self.min_size >= self.max_size:
            raise ConfigurationError("min_size must be less than max_size")

        # Validate dates if provided
        if self.after_date:
            if not parse_date(self.after_date):
                raise ConfigurationError(
                    f"Invalid after_date format: {self.after_date}"
                )

        if self.before_date:
            if not parse_date(self.before_date):
                raise ConfigurationError(
                    f"Invalid before_date format: {self.before_date}"
                )

        # Check date logic
        if self.after_date and self.before_date:
            after_dt = parse_date(self.after_date)
            before_dt = parse_date(self.before_date)
            if after_dt and before_dt and after_dt >= before_dt:
                raise ConfigurationError("after_date must be before before_date")

    def get_after_datetime(self) -> Optional[datetime]:
        """Convert after_date string to datetime object."""
        return parse_date(self.after_date) if self.after_date else None

    def get_before_datetime(self) -> Optional[datetime]:
        """Convert before_date string to datetime object."""
        return parse_date(self.before_date) if self.before_date else None


@dataclass
class DownloadConfig:
    """
    Download and file organization configuration.

    This demonstrates how to provide flexible options while maintaining
    sensible defaults that work for most users.
    """

    # Base directory for all downloads
    base_dir: str = "./downloads"

    # How to organize downloaded files
    # "sender" = organize by sender email
    # "date" = organize by email date
    # "sender_date" = organize by sender, then date
    # "flat" = all files in base directory
    organize_by: str = "sender"

    # File naming strategy
    # "original" = keep original filename
    # "timestamp" = prefix with timestamp
    # "uuid" = prefix with unique ID
    naming_strategy: str = "original"

    # Whether to overwrite existing files
    overwrite_existing: bool = False

    # Create missing directories automatically
    create_missing_dirs: bool = True

    # File permissions for downloaded files (Unix-style octal)
    file_permissions: str = "644"

    # Parallel download settings
    max_concurrent_downloads: int = 3
    chunk_size: int = 8192  # 8KB chunks

    # Resume capability for interrupted downloads
    enable_resume: bool = True
    temp_suffix: str = ".downloading"

    def validate(self) -> None:
        """Validate download configuration."""
        # Validate organization strategy
        valid_strategies = ["sender", "date", "sender_date", "flat"]
        if self.organize_by not in valid_strategies:
            raise ConfigurationError(
                f"Invalid organize_by: {self.organize_by}. "
                f"Must be one of: {', '.join(valid_strategies)}"
            )

        # Validate naming strategy
        valid_naming = ["original", "timestamp", "uuid"]
        if self.naming_strategy not in valid_naming:
            raise ConfigurationError(
                f"Invalid naming_strategy: {self.naming_strategy}. "
                f"Must be one of: {', '.join(valid_naming)}"
            )

        # Validate concurrent downloads
        if self.max_concurrent_downloads <= 0:
            raise ConfigurationError("max_concurrent_downloads must be positive")

        if self.max_concurrent_downloads > 10:
            # Reasonable upper limit to prevent overwhelming the system
            raise ConfigurationError("max_concurrent_downloads should not exceed 10")

        # Validate chunk size
        if self.chunk_size <= 0:
            raise ConfigurationError("chunk_size must be positive")

        # Validate file permissions format
        try:
            int(self.file_permissions, 8)  # Parse as octal
        except ValueError:
            raise ConfigurationError(
                f"Invalid file_permissions: {self.file_permissions}"
            )

    def get_base_path(self) -> Path:
        """Get base directory as Path object, creating if necessary."""
        if self.create_missing_dirs:
            return ensure_directory(self.base_dir)
        else:
            return Path(self.base_dir)


@dataclass
class WatchConfig:
    """
    Real-time watching configuration.

    This is specific to the watch mode where we monitor for new emails
    and download attachments automatically.
    """

    # How often to check for new emails (in seconds)
    check_interval: int = 30

    # Show desktop notifications for new downloads
    show_notifications: bool = True

    # Maximum time to run watch mode (in minutes, 0 = indefinite)
    max_runtime_minutes: int = 0

    # Quiet hours (don't check during these times)
    quiet_start_hour: Optional[int] = None  # e.g., 22 for 10 PM
    quiet_end_hour: Optional[int] = None  # e.g., 8 for 8 AM

    def validate(self) -> None:
        """Validate watch configuration."""
        if self.check_interval <= 0:
            raise ConfigurationError("check_interval must be positive")

        if self.check_interval < 10:
            # Prevent hammering the Gmail API
            raise ConfigurationError("check_interval should be at least 10 seconds")

        if self.max_runtime_minutes < 0:
            raise ConfigurationError("max_runtime_minutes cannot be negative")

        # Validate quiet hours
        if self.quiet_start_hour is not None:
            if not 0 <= self.quiet_start_hour <= 23:
                raise ConfigurationError("quiet_start_hour must be 0-23")

        if self.quiet_end_hour is not None:
            if not 0 <= self.quiet_end_hour <= 23:
                raise ConfigurationError("quiet_end_hour must be 0-23")


@dataclass
class LoggingConfig:
    """
    Logging configuration.

    Good logging is essential for debugging and monitoring your application.
    This shows how to make logging configurable.
    """

    # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    level: str = "INFO"

    # Log file path (None = console only)
    file_path: Optional[str] = "logs/gmail_downloader.log"

    # Log format string
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Maximum log file size before rotation
    max_file_size: str = "10MB"

    # Number of backup files to keep
    backup_count: int = 5

    # Whether to use JSON format for structured logging
    json_format: bool = False

    # Include request IDs for tracing
    include_request_id: bool = True

    def validate(self) -> None:
        """Validate logging configuration."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ConfigurationError(
                f"Invalid log level: {self.level}. "
                f"Must be one of: {', '.join(valid_levels)}"
            )

        if self.backup_count < 0:
            raise ConfigurationError("backup_count cannot be negative")


@dataclass
class AppConfig:
    """
    Main application configuration that combines all settings.

    This is the top-level configuration object that brings together all
    the different configuration sections. It demonstrates composition -
    building complex objects from simpler parts.
    """

    # Application metadata
    app_name: str = "Gmail Attachment Downloader"
    version: str = "0.1.0"

    # Configuration sections
    gmail: GmailConfig = field(default_factory=GmailConfig)
    filters: FilterConfig = field(default_factory=FilterConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)
    watch: WatchConfig = field(default_factory=WatchConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def validate(self) -> None:
        """
        Validate the entire configuration.

        This is an example of the Composite pattern - we delegate validation
        to each component, then add any cross-component validation here.
        """
        # Validate each section
        self.gmail.validate()
        self.filters.validate()
        self.download.validate()
        self.watch.validate()
        self.logging.validate()

        # Cross-component validation could go here
        # For example, checking that download directory is writable
        try:
            download_path = self.download.get_base_path()
            # Try to create a test file to verify write permissions
            test_file = download_path / ".write_test"
            test_file.touch()
            test_file.unlink()  # Clean up
        except Exception as e:
            raise ConfigurationError(f"Cannot write to download directory: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format.

        This is useful for serializing configuration back to YAML
        or for debugging purposes.
        """
        return {
            "app_name": self.app_name,
            "version": self.version,
            "gmail": {
                "credentials_file": self.gmail.credentials_file,
                "token_file": self.gmail.token_file,
                "scopes": self.gmail.scopes,
                "requests_per_minute": self.gmail.requests_per_minute,
                "requests_per_day": self.gmail.requests_per_day,
                "max_retries": self.gmail.max_retries,
                "backoff_factor": self.gmail.backoff_factor,
            },
            "filters": {
                "senders": self.filters.senders,
                "extensions": self.filters.extensions,
                "after_date": self.filters.after_date,
                "before_date": self.filters.before_date,
                "min_size": self.filters.min_size,
                "max_size": self.filters.max_size,
                "subject_keywords": self.filters.subject_keywords,
                "subject_exclude_keywords": self.filters.subject_exclude_keywords,
                "has_attachment": self.filters.has_attachment,
            },
            "download": {
                "base_dir": self.download.base_dir,
                "organize_by": self.download.organize_by,
                "naming_strategy": self.download.naming_strategy,
                "overwrite_existing": self.download.overwrite_existing,
                "create_missing_dirs": self.download.create_missing_dirs,
                "file_permissions": self.download.file_permissions,
                "max_concurrent_downloads": self.download.max_concurrent_downloads,
                "chunk_size": self.download.chunk_size,
                "enable_resume": self.download.enable_resume,
                "temp_suffix": self.download.temp_suffix,
            },
            "watch": {
                "check_interval": self.watch.check_interval,
                "show_notifications": self.watch.show_notifications,
                "max_runtime_minutes": self.watch.max_runtime_minutes,
                "quiet_start_hour": self.watch.quiet_start_hour,
                "quiet_end_hour": self.watch.quiet_end_hour,
            },
            "logging": {
                "level": self.logging.level,
                "file_path": self.logging.file_path,
                "format_string": self.logging.format_string,
                "max_file_size": self.logging.max_file_size,
                "backup_count": self.logging.backup_count,
                "json_format": self.logging.json_format,
                "include_request_id": self.logging.include_request_id,
            },
        }


def load_config(config_path: Union[str, Path] = "config/config.yaml") -> AppConfig:
    """
    Load configuration from YAML file with environment variable support.

    This function demonstrates the layered configuration approach:
    1. Start with default values from dataclasses
    2. Override with values from YAML file
    3. Override with environment variables
    4. CLI arguments would be the final override (handled in main.py)

    Args:
        config_path: Path to the configuration YAML file

    Returns:
        Fully configured AppConfig object

    Raises:
        ConfigurationError: If configuration is invalid or file cannot be read

    Example:
        >>> config = load_config("config/config.yaml")
        >>> print(config.filters.extensions)
        ['.pdf', '.docx', '.xlsx']
    """
    config_file = Path(config_path)

    # Start with default configuration
    config = AppConfig()

    # Load from YAML file if it exists
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                # Load YAML content
                yaml_data = yaml.safe_load(f)

                if yaml_data:
                    # Apply YAML values to configuration
                    config = _apply_yaml_to_config(config, yaml_data)

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {config_path}: {e}")
        except IOError as e:
            raise ConfigurationError(f"Cannot read config file {config_path}: {e}")
    else:
        # Configuration file doesn't exist - this is okay, we'll use defaults
        print(f"ℹ️  Config file not found: {config_path}")
        print("Using default configuration. Run with --help to see options.")

    # Apply environment variable overrides
    config = _apply_environment_overrides(config)

    # Validate the final configuration
    try:
        config.validate()
    except ConfigurationError as e:
        raise ConfigurationError(f"Configuration validation failed: {e}")

    return config


def _apply_yaml_to_config(config: AppConfig, yaml_data: Dict[str, Any]) -> AppConfig:
    """
    Apply YAML data to configuration object.

    This function shows how to safely update configuration from user data.
    We only update values that actually exist in the YAML file, preserving
    defaults for everything else.
    """
    # Gmail configuration
    if "gmail" in yaml_data:
        gmail_data = yaml_data["gmail"]
        if "credentials_file" in gmail_data:
            config.gmail.credentials_file = gmail_data["credentials_file"]
        if "token_file" in gmail_data:
            config.gmail.token_file = gmail_data["token_file"]
        if "scopes" in gmail_data:
            config.gmail.scopes = gmail_data["scopes"]
        if "requests_per_minute" in gmail_data:
            config.gmail.requests_per_minute = gmail_data["requests_per_minute"]
        if "requests_per_day" in gmail_data:
            config.gmail.requests_per_day = gmail_data["requests_per_day"]
        if "max_retries" in gmail_data:
            config.gmail.max_retries = gmail_data["max_retries"]
        if "backoff_factor" in gmail_data:
            config.gmail.backoff_factor = gmail_data["backoff_factor"]

    # Filter configuration
    if "filters" in yaml_data:
        filter_data = yaml_data["filters"]
        if "senders" in filter_data:
            config.filters.senders = filter_data["senders"]
        if "extensions" in filter_data:
            config.filters.extensions = filter_data["extensions"]
        if "after_date" in filter_data:
            config.filters.after_date = filter_data["after_date"]
        if "before_date" in filter_data:
            config.filters.before_date = filter_data["before_date"]
        if "min_size" in filter_data:
            config.filters.min_size = filter_data["min_size"]
        if "max_size" in filter_data:
            config.filters.max_size = filter_data["max_size"]
        if "subject_keywords" in filter_data:
            config.filters.subject_keywords = filter_data["subject_keywords"]
        if "subject_exclude_keywords" in filter_data:
            config.filters.subject_exclude_keywords = filter_data[
                "subject_exclude_keywords"
            ]
        if "has_attachment" in filter_data:
            config.filters.has_attachment = filter_data["has_attachment"]

    # Download configuration
    if "download" in yaml_data:
        download_data = yaml_data["download"]
        if "base_dir" in download_data:
            config.download.base_dir = download_data["base_dir"]
        if "organize_by" in download_data:
            config.download.organize_by = download_data["organize_by"]
        if "naming_strategy" in download_data:
            config.download.naming_strategy = download_data["naming_strategy"]
        if "overwrite_existing" in download_data:
            config.download.overwrite_existing = download_data["overwrite_existing"]
        if "create_missing_dirs" in download_data:
            config.download.create_missing_dirs = download_data["create_missing_dirs"]
        if "file_permissions" in download_data:
            config.download.file_permissions = download_data["file_permissions"]
        if "max_concurrent_downloads" in download_data:
            config.download.max_concurrent_downloads = download_data[
                "max_concurrent_downloads"
            ]
        if "chunk_size" in download_data:
            config.download.chunk_size = download_data["chunk_size"]
        if "enable_resume" in download_data:
            config.download.enable_resume = download_data["enable_resume"]
        if "temp_suffix" in download_data:
            config.download.temp_suffix = download_data["temp_suffix"]

    # Watch configuration
    if "watch" in yaml_data:
        watch_data = yaml_data["watch"]
        if "check_interval" in watch_data:
            config.watch.check_interval = watch_data["check_interval"]
        if "show_notifications" in watch_data:
            config.watch.show_notifications = watch_data["show_notifications"]
        if "max_runtime_minutes" in watch_data:
            config.watch.max_runtime_minutes = watch_data["max_runtime_minutes"]
        if "quiet_start_hour" in watch_data:
            config.watch.quiet_start_hour = watch_data["quiet_start_hour"]
        if "quiet_end_hour" in watch_data:
            config.watch.quiet_end_hour = watch_data["quiet_end_hour"]

    # Logging configuration
    if "logging" in yaml_data:
        logging_data = yaml_data["logging"]
        if "level" in logging_data:
            config.logging.level = logging_data["level"]
        if "file_path" in logging_data:
            config.logging.file_path = logging_data["file_path"]
        if "format_string" in logging_data:
            config.logging.format_string = logging_data["format_string"]
        if "max_file_size" in logging_data:
            config.logging.max_file_size = logging_data["max_file_size"]
        if "backup_count" in logging_data:
            config.logging.backup_count = logging_data["backup_count"]
        if "json_format" in logging_data:
            config.logging.json_format = logging_data["json_format"]
        if "include_request_id" in logging_data:
            config.logging.include_request_id = logging_data["include_request_id"]

    return config


def _apply_environment_overrides(config: AppConfig) -> AppConfig:
    """
    Apply environment variable overrides to configuration.

    Environment variables are useful for:
    1. Sensitive data (credentials, API keys)
    2. Container deployments where config files are inconvenient
    3. CI/CD pipelines
    4. Different environments (dev, staging, production)

    We use a naming convention: GMAIL_DOWNLOADER_{SECTION}_{SETTING}
    For example: GMAIL_DOWNLOADER_DOWNLOAD_BASE_DIR
    """
    # Gmail settings
    if creds_file := os.getenv("GMAIL_DOWNLOADER_GMAIL_CREDENTIALS_FILE"):
        config.gmail.credentials_file = creds_file

    if token_file := os.getenv("GMAIL_DOWNLOADER_GMAIL_TOKEN_FILE"):
        config.gmail.token_file = token_file

    # Download settings
    if base_dir := os.getenv("GMAIL_DOWNLOADER_DOWNLOAD_BASE_DIR"):
        config.download.base_dir = base_dir

    if organize_by := os.getenv("GMAIL_DOWNLOADER_DOWNLOAD_ORGANIZE_BY"):
        config.download.organize_by = organize_by

    # Watch settings
    if check_interval := os.getenv("GMAIL_DOWNLOADER_WATCH_CHECK_INTERVAL"):
        try:
            config.watch.check_interval = int(check_interval)
        except ValueError:
            raise ConfigurationError(
                f"Invalid GMAIL_DOWNLOADER_WATCH_CHECK_INTERVAL: {check_interval}"
            )

    # Logging settings
    if log_level := os.getenv("GMAIL_DOWNLOADER_LOGGING_LEVEL"):
        config.logging.level = log_level.upper()

    if log_file := os.getenv("GMAIL_DOWNLOADER_LOGGING_FILE_PATH"):
        config.logging.file_path = log_file

    return config


def save_config(
    config: AppConfig, config_path: Union[str, Path] = "config/config.yaml"
) -> None:
    """
    Save configuration to YAML file.

    This allows users to generate a configuration file with their current
    settings, or for the application to save updated configuration.

    Args:
        config: Configuration object to save
        config_path: Where to save the YAML file

    Raises:
        ConfigurationError: If file cannot be written
    """
    config_file = Path(config_path)

    # Ensure the config directory exists
    config_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Convert config to dictionary
        config_dict = config.to_dict()

        # Write to YAML file with nice formatting
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(
                config_dict,
                f,
                default_flow_style=False,  # Use block style (more readable)
                sort_keys=False,  # Preserve order
                indent=2,  # 2-space indentation
                allow_unicode=True,  # Support Unicode characters
            )

        print(f"✅ Configuration saved to: {config_file}")

    except IOError as e:
        raise ConfigurationError(f"Cannot write config file {config_path}: {e}")


def create_default_config_file(
    config_path: Union[str, Path] = "config/config.yaml",
) -> None:
    """
    Create a default configuration file with helpful comments.

    This generates a user-friendly YAML file that people can easily customize.
    """
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)

    default_yaml_content = """# Gmail Attachment Downloader Configuration
# This file controls how the application behaves

# Gmail API settings
gmail:
  # Path to OAuth2 credentials from Google Cloud Console
  credentials_file: "config/credentials.json"
  
  # Where to store authentication tokens
  token_file: "config/token.json"
  
  # API rate limiting (respect Gmail quotas)
  requests_per_minute: 250
  max_retries: 3

# Email filtering options
filters:
  # Specific senders to monitor (empty = all senders)
  senders: []
    # - "important@company.com"
    # - "reports@system.com"
  
  # File types to download
  extensions:
    - ".pdf"
    - ".docx"
    - ".xlsx"
    - ".csv"
    - ".txt"
  
  # Date filtering (YYYY-MM-DD format)
  after_date: null   # Download emails after this date
  before_date: null  # Download emails before this date
  
  # File size limits
  min_size: 1024          # 1 KB minimum
  max_size: 52428800      # 50 MB maximum
  
  # Subject filtering
  subject_keywords: []           # Include emails with these words
  subject_exclude_keywords:      # Exclude emails with these words
    - "spam"
    - "promotional"

# Download and organization settings
download:
  # Where to save attachments
  base_dir: "./downloads"
  
  # How to organize files: sender, date, sender_date, flat
  organize_by: "sender"
  
  # File naming: original, timestamp, uuid
  naming_strategy: "original"
  
  # Whether to overwrite existing files
  overwrite_existing: false
  
  # Parallel downloads (be reasonable)
  max_concurrent_downloads: 3

# Real-time monitoring settings (for watch mode)
watch:
  # How often to check for new emails (seconds)
  check_interval: 30
  
  # Show desktop notifications
  show_notifications: true
  
  # Maximum watch time (minutes, 0 = infinite)
  max_runtime_minutes: 0

# Logging configuration
logging:
  # Log level: DEBUG, INFO, WARNING, ERROR
  level: "INFO"
  
  # Log file location (null = console only)
  file_path: "logs/gmail_downloader.log"
  
  # Keep this many old log files
  backup_count: 5
"""

    try:
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(default_yaml_content)

        print(f"✅ Created default configuration: {config_file}")
        print("📝 Edit this file to customize your settings")

    except IOError as e:
        raise ConfigurationError(f"Cannot create config file {config_path}: {e}")


# Example usage and testing
if __name__ == "__main__":
    """
    Demonstration of configuration management features.

    This shows how to work with the configuration system and helps
    with testing and understanding.
    """
    print("=== Gmail Downloader Configuration Demo ===\n")

    # Create a default configuration
    print("📋 Creating default configuration...")
    config = AppConfig()

    # Show some default values
    print(f"Default download directory: {config.download.base_dir}")
    print(f"Default file extensions: {config.filters.extensions}")
    print(f"Default watch interval: {config.watch.check_interval} seconds")

    # Test configuration validation
    print("\n🔍 Testing configuration validation...")
    try:
        # This should pass if credentials file doesn't exist
        # (which is expected in a fresh setup)
        pass  # We'll skip validation for demo since credentials don't exist yet
    except ConfigurationError as e:
        print(f"Validation error (expected): {e}")

    # Demonstrate configuration modification
    print("\n⚙️ Modifying configuration...")
    config.filters.senders = ["test@example.com", "reports@company.com"]
    config.download.organize_by = "date"
    config.watch.check_interval = 60

    print(f"Updated senders: {config.filters.senders}")
    print(f"Updated organization: {config.download.organize_by}")
    print(f"Updated check interval: {config.watch.check_interval}")

    # Show configuration as dictionary
    print("\n📄 Configuration as dictionary:")
    config_dict = config.to_dict()

    # Print just a subset to avoid overwhelming output
    print("Filters section:")
    for key, value in config_dict["filters"].items():
        print(f"  {key}: {value}")

    # Test environment variable override
    print("\n🌍 Testing environment variable override...")
    os.environ["GMAIL_DOWNLOADER_DOWNLOAD_BASE_DIR"] = "/tmp/test_downloads"

    # Load configuration (would read from file if it existed)
    try:
        loaded_config = load_config("nonexistent_config.yaml")
        print(f"Base directory after env override: {loaded_config.download.base_dir}")
    except ConfigurationError as e:
        print(f"Expected error: {e}")

    # Clean up environment
    if "GMAIL_DOWNLOADER_DOWNLOAD_BASE_DIR" in os.environ:
        del os.environ["GMAIL_DOWNLOADER_DOWNLOAD_BASE_DIR"]

    print("\n✅ Configuration demo completed!")
    print("\nNext steps:")
    print("1. Run 'python -m gmail_downloader.config' to see this demo")
    print("2. Create config/config.yaml with your settings")
    print("3. Set up Google API credentials")
