package utils

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSanitizeFilename(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "empty string",
			input:    "",
			expected: "unnamed_file",
		},
		{
			name:     "normal filename",
			input:    "document.pdf",
			expected: "document.pdf",
		},
		{
			name:     "dangerous characters",
			input:    "Contract <FINAL>.pdf",
			expected: "Contract _FINAL_.pdf",
		},
		{
			name:     "unicode characters",
			input:    "résumé.pdf",
			expected: "resume.pdf",
		},
		{
			name:     "windows reserved name",
			input:    "CON.txt",
			expected: "_CON.txt",
		},
		{
			name:     "multiple dangerous chars",
			input:    "file|||name???.txt",
			expected: "file_name_.txt",
		},
		{
			name:     "control characters",
			input:    "file\x00\x01name.txt",
			expected: "file_name.txt",
		},
		{
			name:     "leading/trailing spaces and dots",
			input:    "  .hidden.file.  ",
			expected: "hidden.file",
		},
		{
			name:     "very long filename",
			input:    strings.Repeat("a", 250) + ".pdf",
			expected: strings.Repeat("a", 196) + ".pdf", // 200 total - 4 for .pdf
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := SanitizeFilename(tt.input)
			if result != tt.expected {
				t.Errorf("SanitizeFilename(%q) = %q, expected %q", tt.input, result, tt.expected)
			}
		})
	}
}

func TestFormatFileSize(t *testing.T) {
	tests := []struct {
		name     string
		input    int64
		expected string
	}{
		{
			name:     "zero bytes",
			input:    0,
			expected: "0 B",
		},
		{
			name:     "negative bytes",
			input:    -100,
			expected: "Invalid size",
		},
		{
			name:     "bytes range",
			input:    512,
			expected: "512 B",
		},
		{
			name:     "kilobytes",
			input:    1024,
			expected: "1.00 KB",
		},
		{
			name:     "kilobytes with decimal",
			input:    1536,
			expected: "1.50 KB",
		},
		{
			name:     "megabytes",
			input:    1048576,
			expected: "1.00 MB",
		},
		{
			name:     "large megabytes",
			input:    52428800,
			expected: "50.0 MB",
		},
		{
			name:     "gigabytes",
			input:    1073741824,
			expected: "1.00 GB",
		},
		{
			name:     "large gigabytes",
			input:    107374182400,
			expected: "100 GB",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := FormatFileSize(tt.input)
			if result != tt.expected {
				t.Errorf("FormatFileSize(%d) = %q, expected %q", tt.input, result, tt.expected)
			}
		})
	}
}

func TestTruncateString(t *testing.T) {
	tests := []struct {
		name      string
		text      string
		maxLength int
		suffix    string
		expected  string
	}{
		{
			name:      "short string",
			text:      "short.pdf",
			maxLength: 20,
			suffix:    "...",
			expected:  "short.pdf",
		},
		{
			name:      "exact length",
			text:      "exactly_twenty_chars",
			maxLength: 20,
			suffix:    "...",
			expected:  "exactly_twenty_chars",
		},
		{
			name:      "truncate with default suffix",
			text:      "this_is_a_very_long_filename.pdf",
			maxLength: 20,
			suffix:    "...",
			expected:  "this_is_a_very_lo...",
		},
		{
			name:      "truncate with word boundary",
			text:      "this is a very long filename.pdf",
			maxLength: 20,
			suffix:    "...",
			expected:  "this is a very...",
		},
		{
			name:      "empty string",
			text:      "",
			maxLength: 10,
			suffix:    "...",
			expected:  "",
		},
		{
			name:      "zero max length",
			text:      "test",
			maxLength: 0,
			suffix:    "...",
			expected:  "",
		},
		{
			name:      "suffix longer than max",
			text:      "test",
			maxLength: 2,
			suffix:    "...",
			expected:  "..",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := TruncateString(tt.text, tt.maxLength, tt.suffix)
			if result != tt.expected {
				t.Errorf("TruncateString(%q, %d, %q) = %q, expected %q",
					tt.text, tt.maxLength, tt.suffix, result, tt.expected)
			}
		})
	}
}

func TestEnsureDirectory(t *testing.T) {
	// Use temp directory for tests
	tempDir := t.TempDir()

	tests := []struct {
		name      string
		path      string
		wantError bool
	}{
		{
			name:      "empty path",
			path:      "",
			wantError: true,
		},
		{
			name:      "new directory",
			path:      filepath.Join(tempDir, "new_dir"),
			wantError: false,
		},
		{
			name:      "nested directory",
			path:      filepath.Join(tempDir, "level1", "level2"),
			wantError: false,
		},
		{
			name:      "existing directory",
			path:      tempDir, // Already exists
			wantError: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := EnsureDirectory(tt.path)
			if (err != nil) != tt.wantError {
				t.Errorf("EnsureDirectory(%q) error = %v, wantError %v", tt.path, err, tt.wantError)
				return
			}

			// If no error expected, verify directory exists
			if !tt.wantError && tt.path != "" {
				if info, err := os.Stat(tt.path); err != nil || !info.IsDir() {
					t.Errorf("EnsureDirectory(%q) did not create directory properly", tt.path)
				}
			}
		})
	}
}

func TestCreateUniqueFilename(t *testing.T) {
	// Use temp directory for tests
	tempDir := t.TempDir()

	tests := []struct {
		name           string
		dir            string
		filename       string
		createExisting bool
		expected       string
	}{
		{
			name:           "empty inputs",
			dir:            "",
			filename:       "",
			createExisting: false,
			expected:       "",
		},
		{
			name:           "non-existent file",
			dir:            tempDir,
			filename:       "new_file.txt",
			createExisting: false,
			expected:       "new_file.txt",
		},
		{
			name:           "existing file",
			dir:            tempDir,
			filename:       "existing.txt",
			createExisting: true,
			expected:       "existing_1.txt",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Create existing file if needed
			if tt.createExisting && tt.dir != "" && tt.filename != "" {
				filePath := filepath.Join(tt.dir, tt.filename)
				if f, err := os.Create(filePath); err != nil {
					t.Fatalf("Failed to create test file: %v", err)
				} else {
					f.Close()
				}
			}

			result := CreateUniqueFilename(tt.dir, tt.filename)
			if result != tt.expected {
				t.Errorf("CreateUniqueFilename(%q, %q) = %q, expected %q",
					tt.dir, tt.filename, result, tt.expected)
			}
		})
	}
}

func TestIsValidFilename(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected bool
	}{
		{
			name:     "empty string",
			input:    "",
			expected: false,
		},
		{
			name:     "normal filename",
			input:    "document.pdf",
			expected: true,
		},
		{
			name:     "dangerous characters",
			input:    "file<bad>.pdf",
			expected: false,
		},
		{
			name:     "windows reserved name",
			input:    "CON.txt",
			expected: false,
		},
		{
			name:     "pipe character",
			input:    "file|bad.pdf",
			expected: false,
		},
		{
			name:     "unicode filename",
			input:    "résumé.pdf",
			expected: true,
		},
		{
			name:     "leading dot",
			input:    ".hidden_file",
			expected: false,
		},
		{
			name:     "trailing dot",
			input:    "file.txt.",
			expected: false,
		},
		{
			name:     "leading space",
			input:    " file.txt",
			expected: false,
		},
		{
			name:     "trailing space",
			input:    "file.txt ",
			expected: false,
		},
		{
			name:     "control character",
			input:    "file\x00name.txt",
			expected: false,
		},
		{
			name:     "very long filename",
			input:    strings.Repeat("a", 300) + ".txt",
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := IsValidFilename(tt.input)
			if result != tt.expected {
				t.Errorf("IsValidFilename(%q) = %v, expected %v", tt.input, result, tt.expected)
			}
		})
	}
}

// Benchmark tests
func BenchmarkSanitizeFilename(b *testing.B) {
	filename := "Contract <FINAL> résumé.pdf"
	for i := 0; i < b.N; i++ {
		SanitizeFilename(filename)
	}
}

func BenchmarkFormatFileSize(b *testing.B) {
	size := int64(52428800)
	for i := 0; i < b.N; i++ {
		FormatFileSize(size)
	}
}
