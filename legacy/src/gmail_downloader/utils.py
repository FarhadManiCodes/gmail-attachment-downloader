"""
Utility functions for the Gmail attachment downloader.

This module demonstrates several important Python concepts:
- Type hints for better code documentation and IDE support
- Error handling with try/except blocks
- Regular expressions for pattern matching
- Working with datetime objects
- String manipulation and validation
- Path handling for cross-platform compatibility

"""

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional, Union


def parse_date(date_string: str) -> Optional[datetime]:
    """
    Parse a date string in various common formats and return a datetime object.
    
    This function demonstrates several important concepts:
    1. Defensive programming - handling multiple input formats gracefully
    2. The importance of standardizing data early in your pipeline
    3. How to handle errors without crashing the entire program
    
    Why do we need this? Users might provide dates in many formats:
    - "2024-01-15" (ISO format - most reliable)
    - "01/15/2024" (US format)
    - "15/01/2024" (European format)
    - "2024/01/15" (Another common variant)
    
    Args:
        date_string: The date string to parse
        
    Returns:
        A datetime object if parsing succeeds, None if it fails
        
    Example:
        >>> parse_date("2024-01-15")
        datetime.datetime(2024, 1, 15, 0, 0)
        >>> parse_date("invalid-date")
        None
    """
    # List of date formats to try, ordered from most to least reliable
    # ISO format first because it's unambiguous
    date_formats = [
        "%Y-%m-%d",        # 2024-01-15 (ISO format - best practice)
        "%Y/%m/%d",        # 2024/01/15 
        "%d/%m/%Y",        # 15/01/2024 (European style)
        "%m/%d/%Y",        # 01/15/2024 (US style)
        "%d-%m-%Y",        # 15-01-2024
        "%m-%d-%Y",        # 01-15-2024
        "%Y.%m.%d",        # 2024.01.15
        "%d.%m.%Y",        # 15.01.2024
    ]
    
    # Strip whitespace to be forgiving of user input
    clean_date = date_string.strip()
    
    # Try each format until one works
    for date_format in date_formats:
        try:
            # strptime converts string to datetime using the specified format
            return datetime.strptime(clean_date, date_format)
        except ValueError:
            # This format didn't work, try the next one
            continue
    
    # If we get here, none of the formats worked
    # Returning None allows the calling code to handle this gracefully
    return None


def format_file_size(size_bytes: int) -> str:
    """
    Convert a file size in bytes to a human-readable string.
    
    This function teaches us about:
    1. Making data user-friendly (raw bytes are hard to understand)
    2. Mathematical calculations with logarithms
    3. String formatting for clean output
    4. Edge case handling (what if size is 0?)
    
    Why is this important? Instead of showing "52428800 bytes",
    we can show "50.0 MB" which users understand instantly.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Human-readable string like "1.5 KB", "50.0 MB", etc.
        
    Example:
        >>> format_file_size(1024)
        "1.0 KB"
        >>> format_file_size(1536)
        "1.5 KB"
        >>> format_file_size(52428800)
        "50.0 MB"
    """
    # Handle the edge case of zero bytes
    if size_bytes == 0:
        return "0 B"
    
    # Handle negative values (shouldn't happen, but let's be defensive)
    if size_bytes < 0:
        return "Invalid size"
    
    # Size units in order of magnitude
    # Each unit is 1024 times larger than the previous one
    size_units = ["B", "KB", "MB", "GB", "TB", "PB"]
    
    # Start with the original size and unit index 0 (bytes)
    size = float(size_bytes)
    unit_index = 0
    
    # Keep dividing by 1024 until we get a manageable number
    # We use 1024 instead of 1000 because computers use binary (2^10 = 1024)
    while size >= 1024 and unit_index < len(size_units) - 1:
        size /= 1024.0
        unit_index += 1
    
    # Format with one decimal place for readability
    # The :.1f means "floating point with 1 decimal place"
    return f"{size:.1f} {size_units[unit_index]}"


def sanitize_filename(filename: str) -> str:
    """
    Clean a filename to make it safe for file system operations.
    
    This function demonstrates:
    1. Cross-platform compatibility (different OS have different rules)
    2. String manipulation and character replacement
    3. Unicode handling for international characters
    4. Why input validation is crucial for security
    
    Why do we need this? Email attachments might have names like:
    - "Contract <FINAL>.pdf" (contains illegal < > characters)
    - "Meeting Notes: Q1/Q2 Results.docx" (contains illegal : / characters)
    - "Résumé François.pdf" (Unicode characters that might cause issues)
    
    We need to make these safe while keeping them readable.
    
    Args:
        filename: The original filename from the email
        
    Returns:
        A cleaned filename that's safe to use on all operating systems
        
    Example:
        >>> sanitize_filename("Contract <FINAL>.pdf")
        "Contract_FINAL_.pdf"
        >>> sanitize_filename("Q1/Q2: Results.xlsx")
        "Q1_Q2_Results.xlsx"
    """
    # Start with the original filename, stripped of whitespace
    clean_name = filename.strip()
    
    # Handle empty filenames
    if not clean_name:
        return "unnamed_file"
    
    # Characters that are illegal or problematic on various operating systems
    # Windows: < > : " | ? * \ /
    # Unix/Linux: / (and \0 null character)
    # macOS: : (treated as / in older versions)
    illegal_chars = '<>:"/\\|?*'
    
    # Replace each illegal character with an underscore
    # This preserves the filename structure while making it safe
    for char in illegal_chars:
        clean_name = clean_name.replace(char, '_')
    
    # Handle Unicode characters by normalizing them
    # This converts accented characters to their closest ASCII equivalents
    # For example: "résumé" becomes "resume"
    clean_name = unicodedata.normalize('NFKD', clean_name)
    
    # Keep only ASCII characters (removes accent marks, etc.)
    # This ensures compatibility across all systems
    clean_name = clean_name.encode('ascii', 'ignore').decode('ascii')
    
    # Replace multiple consecutive underscores with a single one
    # This prevents ugly filenames like "file___name.txt"
    clean_name = re.sub(r'_+', '_', clean_name)
    
    # Remove leading/trailing underscores and dots
    # Leading dots make files hidden on Unix systems
    clean_name = clean_name.strip('_.')
    
    # Ensure we still have something left
    if not clean_name:
        return "unnamed_file"
    
    # Limit length to prevent filesystem issues (most support 255 chars)
    # Keep some buffer for extensions and path length
    max_length = 200
    if len(clean_name) > max_length:
        # Try to preserve the file extension
        if '.' in clean_name:
            name_part, ext_part = clean_name.rsplit('.', 1)
            available_length = max_length - len(ext_part) - 1
            clean_name = name_part[:available_length] + '.' + ext_part
        else:
            clean_name = clean_name[:max_length]
    
    return clean_name


def is_valid_email(email: str) -> bool:
    """
    Validate if a string looks like a proper email address.
    
    This function teaches us about:
    1. Regular expressions for pattern matching
    2. Input validation (never trust user input!)
    3. The difference between simple validation and RFC-compliant validation
    4. Balancing simplicity with accuracy
    
    Note: This is a simple validation. Perfect email validation is incredibly
    complex (the full RFC 5322 specification is thousands of lines). For our
    use case, we just need to catch obvious mistakes and malformed addresses.
    
    Args:
        email: The email address string to validate
        
    Returns:
        True if the email looks valid, False otherwise
        
    Example:
        >>> is_valid_email("user@example.com")
        True
        >>> is_valid_email("not-an-email")
        False
        >>> is_valid_email("user@")
        False
    """
    # Handle edge cases first
    if not email or not isinstance(email, str):
        return False
    
    # Clean the email by removing extra whitespace
    email = email.strip()
    
    # Basic length check (emails can't be too short or too long)
    if len(email) < 5 or len(email) > 254:  # RFC 5321 limit
        return False
    
    # Simple but effective email pattern
    # Let's break this down piece by piece:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # Pattern explanation:
    # ^                    - Start of string
    # [a-zA-Z0-9._%+-]+   - Local part: letters, numbers, and common symbols
    # @                    - The @ symbol (required)
    # [a-zA-Z0-9.-]+      - Domain name: letters, numbers, dots, hyphens
    # \.                   - A literal dot (escaped because . means "any char")
    # [a-zA-Z]{2,}        - Top-level domain: at least 2 letters
    # $                    - End of string
    
    # Use the re.match function to test our pattern
    return bool(re.match(pattern, email))


def extract_email_address(full_email: str) -> str:
    """
    Extract clean email address from various formats.
    
    Email headers can contain emails in different formats:
    - "john@example.com" (simple)
    - "John Doe <john@example.com>" (with display name)
    - "<john@example.com>" (just brackets)
    
    This function demonstrates string parsing and handling real-world data messiness.
    
    Args:
        full_email: Email string in any format
        
    Returns:
        Clean email address or original string if no email found
        
    Example:
        >>> extract_email_address("John Doe <john@example.com>")
        "john@example.com"
        >>> extract_email_address("john@example.com")
        "john@example.com"
    """
    # Handle empty input
    if not full_email:
        return ""
    
    # Clean up whitespace
    clean_email = full_email.strip()
    
    # Look for email address inside angle brackets < >
    # This handles the "Name <email@domain.com>" format
    bracket_match = re.search(r'<(.+?)>', clean_email)
    if bracket_match:
        extracted = bracket_match.group(1).strip()
        # Return the extracted email if it looks valid
        if is_valid_email(extracted):
            return extracted.lower()
    
    # If no brackets, assume the whole string is the email
    # Convert to lowercase for consistency
    potential_email = clean_email.lower()
    
    # Return it if it looks like a valid email
    if is_valid_email(potential_email):
        return potential_email
    
    # If nothing worked, return the original (let caller decide what to do)
    return full_email


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    This function shows us:
    1. Working with file system paths safely
    2. Cross-platform path handling using pathlib
    3. Error handling for file system operations
    4. Why we need to create directories before writing files
    
    Args:
        path: Directory path as string or Path object
        
    Returns:
        Path object representing the directory
        
    Raises:
        OSError: If directory cannot be created due to permissions or other issues
        
    Example:
        >>> ensure_directory("downloads/attachments")
        PosixPath('downloads/attachments')
    """
    # Convert string to Path object if needed
    # pathlib.Path is the modern, cross-platform way to handle file paths
    directory = Path(path)
    
    try:
        # Create the directory and any necessary parent directories
        # parents=True means "create parent directories if they don't exist"
        # exist_ok=True means "don't raise an error if directory already exists"
        directory.mkdir(parents=True, exist_ok=True)
        
        # Return the Path object for further use
        return directory
        
    except PermissionError:
        # More specific error message for permission issues
        raise OSError(f"Permission denied: Cannot create directory '{directory}'")
    except OSError as e:
        # Re-raise other OS errors with more context
        raise OSError(f"Failed to create directory '{directory}': {e}")


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length, adding a suffix if truncated.
    
    This is useful for displaying long filenames or email subjects in logs
    or user interfaces without overwhelming the display.
    
    Args:
        text: The string to potentially truncate
        max_length: Maximum allowed length (including suffix)
        suffix: What to add when truncating (default: "...")
        
    Returns:
        Original string if short enough, or truncated string with suffix
        
    Example:
        >>> truncate_string("This is a very long filename.pdf", 20)
        "This is a very lo..."
        >>> truncate_string("Short.pdf", 20)
        "Short.pdf"
    """
    # Handle edge cases
    if not text or max_length <= 0:
        return ""
    
    # If the text is already short enough, return it unchanged
    if len(text) <= max_length:
        return text
    
    # Calculate how much space we have for actual content
    # We need to reserve space for the suffix
    available_length = max_length - len(suffix)
    
    # If there's no room for content + suffix, just return the suffix
    if available_length <= 0:
        return suffix[:max_length]
    
    # Truncate and add suffix
    return text[:available_length] + suffix


# Example usage and testing section
# This shows how professional code often includes examples for learning
if __name__ == "__main__":
    """
    This section runs only when the file is executed directly (not imported).
    It's a great way to test your functions and provide examples for learning.
    
    Try running: python src/gmail_downloader/utils.py
    """
    print("=== Gmail Downloader Utils Demo ===\n")
    
    # Test date parsing
    print("📅 Date Parsing Examples:")
    test_dates = ["2024-01-15", "01/15/2024", "15/01/2024", "invalid-date"]
    for date_str in test_dates:
        result = parse_date(date_str)
        print(f"  '{date_str}' → {result}")
    
    print("\n📊 File Size Formatting Examples:")
    test_sizes = [0, 512, 1024, 1536, 1048576, 52428800, 1073741824]
    for size in test_sizes:
        formatted = format_file_size(size)
        print(f"  {size:>10} bytes → {formatted}")
    
    print("\n🧹 Filename Sanitization Examples:")
    test_filenames = [
        "Contract <FINAL>.pdf",
        "Q1/Q2: Results.xlsx", 
        "Résumé François.pdf",
        "file|||name???.txt"
    ]
    for filename in test_filenames:
        clean = sanitize_filename(filename)
        print(f"  '{filename}' → '{clean}'")
    
    print("\n📧 Email Validation Examples:")
    test_emails = [
        "user@example.com",
        "John Doe <john@example.com>",
        "invalid-email",
        "<test@domain.org>",
        "not.an.email"
    ]
    for email in test_emails:
        is_valid = is_valid_email(extract_email_address(email))
        extracted = extract_email_address(email)
        print(f"  '{email}' → '{extracted}' (valid: {is_valid})")
    
    print("\n📁 Directory Creation Example:")
    test_path = "test_downloads/attachments"
    try:
        created_path = ensure_directory(test_path)
        print(f"  Created: {created_path}")
        # Clean up the test directory
        created_path.rmdir()
        created_path.parent.rmdir()
        print(f"  Cleaned up test directory")
    except OSError as e:
        print(f"  Error: {e}")
    
    print("\n✂️ String Truncation Examples:")
    test_strings = [
        "Short filename.pdf",
        "This is a very long filename that should be truncated.pdf",
        "Medium length name.docx"
    ]
    for text in test_strings:
        truncated = truncate_string(text, 25)
        print(f"  '{text}' → '{truncated}'")
