"""
Comprehensive tests for utils.py module.

This file demonstrates professional testing practices:
- Testing edge cases and boundary conditions
- Testing both success and failure scenarios
- Using parametrized tests for multiple inputs
- Clear test names that describe what's being tested
- Proper test organization and documentation
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from typing import Generator, Optional

# Import the functions we want to test
from gmail_downloader.utils import (
    parse_date,
    format_file_size,
    sanitize_filename,
    is_valid_email,
    extract_email_address,
    ensure_directory,
    truncate_string,
)


class TestParseDate:
    """Test the parse_date function with various inputs and edge cases."""

    def test_valid_iso_format(self) -> None:
        """Test ISO format date parsing (most reliable format)."""
        result = parse_date("2024-01-15")
        expected = datetime(2024, 1, 15)
        assert result == expected

    def test_valid_slash_formats(self) -> None:
        """Test various slash-separated date formats."""
        # Year/Month/Day
        assert parse_date("2024/01/15") == datetime(2024, 1, 15)

        # Day/Month/Year (European style)
        assert parse_date("15/01/2024") == datetime(2024, 1, 15)

        # Month/Day/Year (US style)
        # Note: This is ambiguous - 01/15/2024 could be Jan 15 or impossible date
        assert parse_date("01/15/2024") == datetime(2024, 1, 15)

    def test_valid_dash_formats(self) -> None:
        """Test dash-separated date formats."""
        assert parse_date("15-01-2024") == datetime(2024, 1, 15)
        assert parse_date("01-15-2024") == datetime(2024, 1, 15)

    def test_valid_dot_formats(self) -> None:
        """Test dot-separated date formats."""
        assert parse_date("2024.01.15") == datetime(2024, 1, 15)
        assert parse_date("15.01.2024") == datetime(2024, 1, 15)

    def test_invalid_dates(self) -> None:
        """Test that invalid dates return None."""
        invalid_dates = [
            "not-a-date",
            "2024-13-01",  # Invalid month
            "2024-02-30",  # Invalid day for February
            "32/01/2024",  # Invalid day
            "01/32/2024",  # Invalid day
            "",  # Empty string
            "2024",  # Incomplete date
            "01-01",  # Incomplete date
            "2024/01",  # Incomplete date
        ]

        for invalid_date in invalid_dates:
            assert parse_date(invalid_date) is None

    def test_whitespace_handling(self) -> None:
        """Test that whitespace is handled gracefully."""
        assert parse_date("  2024-01-15  ") == datetime(2024, 1, 15)
        assert parse_date("\t2024-01-15\n") == datetime(2024, 1, 15)

    def test_edge_case_dates(self) -> None:
        """Test edge case dates like leap years."""
        # Leap year
        assert parse_date("2024-02-29") == datetime(2024, 2, 29)

        # Non-leap year (should be invalid)
        assert parse_date("2023-02-29") is None

        # Year boundaries
        assert parse_date("1999-12-31") == datetime(1999, 12, 31)
        assert parse_date("2000-01-01") == datetime(2000, 1, 1)


class TestFormatFileSize:
    """Test the format_file_size function with various inputs."""

    def test_zero_bytes(self) -> None:
        """Test zero byte formatting."""
        assert format_file_size(0) == "0 B"

    def test_negative_bytes(self) -> None:
        """Test negative byte handling."""
        assert format_file_size(-100) == "Invalid size"
        assert format_file_size(-1) == "Invalid size"

    def test_bytes_range(self) -> None:
        """Test formatting in bytes range."""
        assert format_file_size(1) == "1.0 B"
        assert format_file_size(512) == "512.0 B"
        assert format_file_size(1023) == "1023.0 B"

    def test_kilobytes_range(self) -> None:
        """Test formatting in kilobytes range."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"  # 1.5 KB
        assert format_file_size(2048) == "2.0 KB"

    def test_megabytes_range(self) -> None:
        """Test formatting in megabytes range."""
        assert format_file_size(1048576) == "1.0 MB"  # 1024^2
        assert format_file_size(52428800) == "50.0 MB"
        assert format_file_size(1073741823) == "1024.0 MB"  # Just under 1 GB

    def test_gigabytes_range(self) -> None:
        """Test formatting in gigabytes range."""
        assert format_file_size(1073741824) == "1.0 GB"  # 1024^3
        assert format_file_size(2147483648) == "2.0 GB"

    def test_large_sizes(self) -> None:
        """Test very large file sizes."""
        # Terabyte
        tb_size = 1024**4
        assert format_file_size(tb_size) == "1.0 TB"

        # Petabyte
        pb_size = 1024**5
        assert format_file_size(pb_size) == "1.0 PB"

    def test_decimal_precision(self) -> None:
        """Test that decimal precision is correct."""
        # Test that we get exactly one decimal place
        result = format_file_size(1536)  # 1.5 KB
        assert "1.5" in result

        # Test rounding
        result = format_file_size(1740)  # Should be ~1.7 KB
        assert "1.7" in result


class TestSanitizeFilename:
    """Test the sanitize_filename function with various problematic inputs."""

    def test_simple_valid_filename(self) -> None:
        """Test that valid filenames pass through unchanged."""
        assert sanitize_filename("document.pdf") == "document.pdf"
        assert sanitize_filename("report_2024.xlsx") == "report_2024.xlsx"

    def test_illegal_characters(self) -> None:
        """Test removal of illegal characters."""
        # Windows illegal characters
        assert sanitize_filename("file<name>.pdf") == "file_name_.pdf"
        assert sanitize_filename("file>name.pdf") == "file_name_.pdf"
        assert sanitize_filename("file:name.pdf") == "file_name.pdf"
        assert sanitize_filename('file"name.pdf') == "file_name.pdf"
        assert sanitize_filename("file|name.pdf") == "file_name.pdf"
        assert sanitize_filename("file?name.pdf") == "file_name.pdf"
        assert sanitize_filename("file*name.pdf") == "file_name.pdf"
        assert sanitize_filename("file\\name.pdf") == "file_name.pdf"
        assert sanitize_filename("file/name.pdf") == "file_name.pdf"

    def test_multiple_illegal_characters(self) -> None:
        """Test filenames with multiple illegal characters."""
        assert sanitize_filename("file<>:|name.pdf") == "file____name.pdf"
        assert (
            sanitize_filename("really*bad?file|name.pdf") == "really_bad_file_name.pdf"
        )

    def test_unicode_characters(self) -> None:
        """Test Unicode character handling."""
        # Accented characters should be converted to ASCII equivalents
        result = sanitize_filename("résumé.pdf")
        assert "resume" in result.lower()

        # Other Unicode characters
        result = sanitize_filename("file_naïve.pdf")
        assert "naive" in result.lower()

    def test_empty_and_whitespace(self) -> None:
        """Test empty strings and whitespace-only strings."""
        assert sanitize_filename("") == "unnamed_file"
        assert sanitize_filename("   ") == "unnamed_file"
        assert sanitize_filename("\t\n") == "unnamed_file"

    def test_leading_trailing_issues(self) -> None:
        """Test removal of leading/trailing problematic characters."""
        assert sanitize_filename(".hidden_file.txt") == "hidden_file.txt"
        assert sanitize_filename("_file_.txt") == "file.txt"
        assert sanitize_filename("..file..txt") == "file.txt"

    def test_multiple_underscores(self) -> None:
        """Test consolidation of multiple underscores."""
        assert sanitize_filename("file___name.pdf") == "file_name.pdf"
        assert sanitize_filename("file<>?*name.pdf") == "file_name.pdf"

    def test_length_limitation(self) -> None:
        """Test that very long filenames are truncated."""
        # Create a very long filename
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)

        # Should be truncated but preserve extension
        assert len(result) <= 204  # 200 + ".pdf"
        assert result.endswith(".pdf")

    def test_extension_preservation(self) -> None:
        """Test that file extensions are preserved during truncation."""
        long_name = "very_long_filename_" * 20 + ".docx"
        result = sanitize_filename(long_name)

        assert result.endswith(".docx")
        assert len(result) <= 205  # 200 + ".docx"

    def test_no_extension_handling(self) -> None:
        """Test files without extensions."""
        long_name = "x" * 300
        result = sanitize_filename(long_name)

        assert len(result) <= 200
        assert result == "x" * 200


class TestIsValidEmail:
    """Test the is_valid_email function with various email formats."""

    def test_valid_emails(self) -> None:
        """Test various valid email formats."""
        valid_emails = [
            "user@example.com",
            "test.email@domain.org",
            "user+tag@example.co.uk",
            "123@numbers.com",
            "a@b.co",  # Minimal valid email
            "user_name@example-domain.com",
            "firstname.lastname@company.net",
        ]

        for email in valid_emails:
            assert is_valid_email(email), f"Should be valid: {email}"

    def test_invalid_emails(self) -> None:
        """Test various invalid email formats."""
        invalid_emails = [
            "not-an-email",
            "@example.com",  # Missing local part
            "user@",  # Missing domain
            "user@@example.com",  # Double @
            "user@.com",  # Missing domain name
            "user@example.",  # Missing TLD
            "user@example.c",  # TLD too short
            "",  # Empty string
            "user name@example.com",  # Space in local part
            "user@exam ple.com",  # Space in domain
            "user@",  # Incomplete
            "a" * 250 + "@example.com",  # Too long
        ]

        for email in invalid_emails:
            assert not is_valid_email(email), f"Should be invalid: {email}"

    def test_edge_cases(self) -> None:
        """Test edge cases for email validation."""
        # None and non-string inputs
        assert not is_valid_email(None)
        assert not is_valid_email(123)
        assert not is_valid_email([])

        # Very short emails
        assert not is_valid_email("a@b")  # Too short overall
        assert is_valid_email("a@b.co")  # Just long enough

    def test_whitespace_handling(self) -> None:
        """Test that whitespace is handled correctly."""
        assert is_valid_email("  user@example.com  ")
        assert not is_valid_email("user @example.com")  # Space in middle


class TestExtractEmailAddress:
    """Test the extract_email_address function with various formats."""

    def test_simple_email(self) -> None:
        """Test extraction from simple email address."""
        assert extract_email_address("user@example.com") == "user@example.com"

    def test_bracketed_email(self) -> None:
        """Test extraction from bracketed format."""
        assert extract_email_address("<user@example.com>") == "user@example.com"
        assert (
            extract_email_address("John Doe <john@example.com>") == "john@example.com"
        )

    def test_name_and_email_format(self) -> None:
        """Test extraction from 'Name <email>' format."""
        result = extract_email_address("John Smith <john.smith@company.com>")
        assert result == "john.smith@company.com"

        result = extract_email_address("Jane Doe <jane@example.org>")
        assert result == "jane@example.org"

    def test_case_normalization(self) -> None:
        """Test that emails are converted to lowercase."""
        assert extract_email_address("USER@EXAMPLE.COM") == "user@example.com"
        assert extract_email_address("John <USER@EXAMPLE.COM>") == "user@example.com"

    def test_invalid_input(self) -> None:
        """Test handling of invalid input."""
        assert extract_email_address("") == ""
        assert extract_email_address("Not an email") == "Not an email"
        assert extract_email_address("John Doe") == "John Doe"

    def test_edge_cases(self) -> None:
        """Test edge cases for email extraction."""
        # Empty brackets
        assert extract_email_address("<>") == "<>"

        # Multiple brackets (should extract first)
        result = extract_email_address("Name <first@example.com> <second@example.com>")
        assert result == "first@example.com"


class TestEnsureDirectory:
    """Test the ensure_directory function with various scenarios."""

    def test_create_new_directory(self) -> None:
        """Test creating a new directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "new_dir"

            # Directory shouldn't exist initially
            assert not test_path.exists()

            # Create it
            result = ensure_directory(test_path)

            # Should exist now and return Path object
            assert test_path.exists()
            assert test_path.is_dir()
            assert isinstance(result, Path)
            assert result == test_path

    def test_create_nested_directories(self) -> None:
        """Test creating nested directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "level1" / "level2" / "level3"

            # Create nested structure
            result = ensure_directory(test_path)

            # All levels should exist
            assert test_path.exists()
            assert test_path.is_dir()
            assert result == test_path

    def test_existing_directory(self) -> None:
        """Test that existing directories are handled gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir)

            # Directory already exists
            assert test_path.exists()

            # Should not raise error
            result = ensure_directory(test_path)
            assert result == test_path

    def test_string_input(self) -> None:
        """Test that string paths are handled correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path_str = os.path.join(temp_dir, "string_test")

            result = ensure_directory(test_path_str)

            # Should convert to Path and create directory
            assert isinstance(result, Path)
            assert result.exists()
            assert result.is_dir()

    def test_permission_error(self) -> None:
        """Test handling of permission errors."""
        # Try to create directory in a location we can't write to
        # This test might not work on all systems, so we'll make it conditional
        try:
            # Try to create in root directory (should fail on most systems)
            if os.name != "nt":  # Skip on Windows as behavior is different
                with pytest.raises(OSError):
                    ensure_directory("/root/test_no_permission")
        except PermissionError:
            # This is expected behavior
            pass


class TestTruncateString:
    """Test the truncate_string function with various inputs."""

    def test_short_string(self) -> None:
        """Test that short strings are not truncated."""
        short_text = "short.pdf"
        result = truncate_string(short_text, 20)
        assert result == short_text

    def test_exact_length(self) -> None:
        """Test string that is exactly the maximum length."""
        text = "exactly_twenty_chars"  # 20 characters
        result = truncate_string(text, 20)
        assert result == text

    def test_long_string_truncation(self) -> None:
        """Test that long strings are truncated properly."""
        long_text = "this_is_a_very_long_filename_that_should_be_truncated.pdf"
        result = truncate_string(long_text, 30)

        assert len(result) == 30
        assert result.endswith("...")
        assert result.startswith("this_is_a_very_long_fi")

    def test_custom_suffix(self) -> None:
        """Test truncation with custom suffix."""
        long_text = "very_long_filename.pdf"
        result = truncate_string(long_text, 15, suffix="[...]")

        assert len(result) == 15
        assert result.endswith("[...]")

    def test_edge_cases(self) -> None:
        """Test edge cases for truncation."""
        # Empty string
        assert truncate_string("", 10) == ""

        # Zero max length
        assert truncate_string("test", 0) == ""

        # Negative max length
        assert truncate_string("test", -5) == ""

    def test_suffix_longer_than_max_length(self) -> None:
        """Test when suffix is longer than max length."""
        result = truncate_string("test", 5, suffix="very_long_suffix")
        # Should return truncated suffix
        assert len(result) <= 5

    def test_max_length_smaller_than_suffix(self) -> None:
        """Test when max_length is smaller than suffix length."""
        result = truncate_string("test_string", 2, suffix="...")
        # Should return truncated suffix since there's no room for content
        assert result == ".."


# Test fixtures and helpers
@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for tests that need file system access."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


# Parametrized tests for comprehensive coverage
@pytest.mark.parametrize(
    "date_string,expected",
    [
        ("2024-01-15", datetime(2024, 1, 15)),
        ("2024/01/15", datetime(2024, 1, 15)),
        ("15/01/2024", datetime(2024, 1, 15)),
        ("invalid", None),
        ("", None),
    ],
)
def test_parse_date_parametrized(date_string: str, expected: Optional[datetime]) -> None:
    """Parametrized test for parse_date function."""
    assert parse_date(date_string) == expected


@pytest.mark.parametrize(
    "size,expected_unit",
    [
        (0, "B"),
        (512, "B"),
        (1024, "KB"),
        (1048576, "MB"),
        (1073741824, "GB"),
    ],
)
def test_format_file_size_units(size: int, expected_unit: str) -> None:
    """Parametrized test for file size units."""
    result = format_file_size(size)
    assert expected_unit in result


@pytest.mark.parametrize(
    "filename,should_change",
    [
        ("normal_file.pdf", False),
        ("file<bad>.pdf", True),
        ("file|bad.pdf", True),
        ("résumé.pdf", True),  # Unicode changes
        ("", True),  # Empty becomes unnamed_file
    ],
)
def test_sanitize_filename_parametrized(filename: str, should_change: bool) -> None:
    """Parametrized test for filename sanitization."""
    result = sanitize_filename(filename)
    if should_change:
        assert result != filename
    else:
        assert result == filename


if __name__ == "__main__":
    """
    Run tests when executed directly.

    This allows running: python tests/test_utils.py
    """
    pytest.main([__file__, "-v"])
