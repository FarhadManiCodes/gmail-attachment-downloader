// File utilities with cross-platform safety and edge case handling
package utils

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
	"unicode"
)

// SanitizeFilename creates safe filename for all platforms
func SanitizeFilename(filename string) string {
	if filename == "" {
		return "unnamed_file"
	}
	
	// Strip whitespace from input
	clean := strings.TrimSpace(filename)
	if clean == "" {
		return "unnamed_file"
	}
	
	// Replace dangerous characters for cross-platform safety first
	// Windows: < > : " | ? * \ /
	// Unix/Linux: / (and null character)
	// macOS: : (treated as / in older versions)
	dangerous := regexp.MustCompile(`[<>:"|?*\\/]`)
	safe := dangerous.ReplaceAllString(clean, "_")
	
	// Handle control characters (ASCII 0-31, 127) and non-printable Unicode
	// Note: Each control character becomes one underscore (don't consolidate yet)
	safe = strings.Map(func(r rune) rune {
		if r < 32 || r == 127 { // Control characters
			return '_'
		}
		if !unicode.IsPrint(r) { // Non-printable Unicode characters
			return '_'
		}
		return r
	}, safe)
	
	// Normalize Unicode characters to ASCII equivalents where possible
	safe = normalizeUnicode(safe)
	
	// Replace multiple consecutive underscores with single underscore
	multiUnderscore := regexp.MustCompile(`_+`)
	safe = multiUnderscore.ReplaceAllString(safe, "_")
	
	// Remove leading/trailing underscores and dots
	// Leading dots make files hidden on Unix systems
	safe = strings.Trim(safe, "_.")
	
	// Ensure we still have something left
	if safe == "" {
		safe = "unnamed_file"
	}
	
	// Limit length to prevent filesystem issues (most support 255 bytes)
	// Keep some buffer for extensions and path length
	maxLength := 200
	if len(safe) > maxLength {
		// Try to preserve the file extension
		if dotIndex := strings.LastIndex(safe, "."); dotIndex != -1 {
			namePart := safe[:dotIndex]
			extPart := safe[dotIndex:]
			availableLength := maxLength - len(extPart)
			if availableLength > 0 {
				safe = namePart[:availableLength] + extPart
			} else {
				// Extension is too long, truncate the whole thing
				safe = safe[:maxLength]
			}
		} else {
			safe = safe[:maxLength]
		}
	}
	
	// Check for Windows reserved names (case-insensitive) after processing
	reservedNames := []string{
		"CON", "PRN", "AUX", "NUL",
		"COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
		"LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
	}
	
	// Extract base name without extension for reserved name check
	baseName := safe
	if dotIndex := strings.LastIndex(safe, "."); dotIndex != -1 {
		baseName = safe[:dotIndex]
	}
	
	upperBaseName := strings.ToUpper(baseName)
	for _, reserved := range reservedNames {
		if upperBaseName == reserved {
			safe = "_" + safe
			break
		}
	}
	
	// Final validation - ensure it's not empty and doesn't end with space or dot
	safe = strings.TrimRight(safe, " .")
	if safe == "" {
		safe = "unnamed_file"
	}
	
	return safe
}

// normalizeUnicode converts accented characters to their ASCII equivalents
func normalizeUnicode(s string) string {
	// Simple ASCII transliteration for common accented characters
	replacements := map[rune]string{
		'à': "a", 'á': "a", 'â': "a", 'ã': "a", 'ä': "a", 'å': "a",
		'è': "e", 'é': "e", 'ê': "e", 'ë': "e",
		'ì': "i", 'í': "i", 'î': "i", 'ï': "i",
		'ò': "o", 'ó': "o", 'ô': "o", 'õ': "o", 'ö': "o",
		'ù': "u", 'ú': "u", 'û': "u", 'ü': "u",
		'ý': "y", 'ÿ': "y",
		'ñ': "n", 'ç': "c",
		'À': "A", 'Á': "A", 'Â': "A", 'Ã': "A", 'Ä': "A", 'Å': "A",
		'È': "E", 'É': "E", 'Ê': "E", 'Ë': "E",
		'Ì': "I", 'Í': "I", 'Î': "I", 'Ï': "I",
		'Ò': "O", 'Ó': "O", 'Ô': "O", 'Õ': "O", 'Ö': "O",
		'Ù': "U", 'Ú': "U", 'Û': "U", 'Ü': "U",
		'Ý': "Y", 'Ÿ': "Y",
		'Ñ': "N", 'Ç': "C",
	}
	
	var result strings.Builder
	for _, r := range s {
		if replacement, exists := replacements[r]; exists {
			result.WriteString(replacement)
		} else if r < 128 { // ASCII character
			result.WriteRune(r)
		} else {
			// Non-ASCII character without replacement, use underscore
			result.WriteRune('_')
		}
	}
	
	return result.String()
}

// EnsureDirectory creates directory path with proper permissions
func EnsureDirectory(path string) error {
	if path == "" {
		return fmt.Errorf("empty path provided")
	}
	
	// Convert to absolute path for consistency
	absPath, err := filepath.Abs(path)
	if err != nil {
		return fmt.Errorf("failed to resolve absolute path for %q: %w", path, err)
	}
	
	// Check if path already exists
	if info, err := os.Stat(absPath); err == nil {
		if !info.IsDir() {
			return fmt.Errorf("path %q exists but is not a directory", absPath)
		}
		// Directory already exists, nothing to do
		return nil
	}
	
	// Create directory with proper permissions
	if err := os.MkdirAll(absPath, 0755); err != nil {
		return fmt.Errorf("failed to create directory %q: %w", absPath, err)
	}
	
	// Verify the directory was created successfully
	if info, err := os.Stat(absPath); err != nil {
		return fmt.Errorf("directory creation appeared to succeed but cannot stat %q: %w", absPath, err)
	} else if !info.IsDir() {
		return fmt.Errorf("path %q was created but is not a directory", absPath)
	}
	
	return nil
}

// FormatFileSize returns human-readable size with appropriate units
func FormatFileSize(bytes int64) string {
	// Handle edge cases
	if bytes == 0 {
		return "0 B"
	}
	
	if bytes < 0 {
		return "Invalid size"
	}
	
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	
	units := []string{"B", "KB", "MB", "GB", "TB", "PB"}
	size := float64(bytes)
	i := 0
	
	for size >= unit && i < len(units)-1 {
		size /= unit
		i++
	}
	
	// Smart precision based on size (matches Python reference)
	if size >= 100 {
		return fmt.Sprintf("%.0f %s", size, units[i])
	} else if size >= 10 {
		return fmt.Sprintf("%.1f %s", size, units[i])
	}
	return fmt.Sprintf("%.2f %s", size, units[i])
}

// TruncateString truncates a string to a maximum length with smart word boundary handling
func TruncateString(text string, maxLength int, suffix string) string {
	// Handle edge cases
	if text == "" || maxLength <= 0 {
		return ""
	}
	
	// If text is already short enough, return unchanged
	if len(text) <= maxLength {
		return text
	}
	
	// Calculate available space for actual content
	suffixLen := len(suffix)
	availableLength := maxLength - suffixLen
	
	// If there's no room for content + suffix, return truncated suffix
	if availableLength <= 0 {
		if suffixLen > maxLength {
			return suffix[:maxLength]
		}
		return suffix
	}
	
	// Try to find a good word boundary for truncation
	truncated := text[:availableLength]
	
	// Look for a space within the last 20% of the available length
	// This prevents cutting words in the middle when possible
	searchStart := int(float64(availableLength) * 0.8)
	if searchStart < 0 {
		searchStart = 0
	}
	
	// Find the last space in the search region
	lastSpaceIndex := -1
	for i := availableLength - 1; i >= searchStart; i-- {
		if text[i] == ' ' {
			lastSpaceIndex = i
			break
		}
	}
	
	// If we found a good word boundary, use it
	if lastSpaceIndex > 0 {
		truncated = text[:lastSpaceIndex]
	}
	
	// Remove trailing whitespace from truncated text
	truncated = strings.TrimRight(truncated, " ")
	
	return truncated + suffix
}

// CreateUniqueFilename generates a unique filename when file exists
func CreateUniqueFilename(dir, filename string) string {
	if dir == "" || filename == "" {
		return filename
	}
	
	fullPath := filepath.Join(dir, filename)
	
	// If file doesn't exist, return original filename
	if _, err := os.Stat(fullPath); os.IsNotExist(err) {
		return filename
	}
	
	// File exists, need to generate unique name
	// Split filename into base and extension
	ext := filepath.Ext(filename)
	base := strings.TrimSuffix(filename, ext)
	
	// Try adding counter suffix: file.txt -> file_1.txt -> file_2.txt
	counter := 1
	maxAttempts := 1000 // Prevent infinite loops
	
	for counter <= maxAttempts {
		newFilename := fmt.Sprintf("%s_%d%s", base, counter, ext)
		newFullPath := filepath.Join(dir, newFilename)
		
		if _, err := os.Stat(newFullPath); os.IsNotExist(err) {
			return newFilename
		}
		
		counter++
	}
	
	// If we've reached max attempts, add timestamp to ensure uniqueness
	timestamp := fmt.Sprintf("%d", time.Now().UnixNano())
	return fmt.Sprintf("%s_%s%s", base, timestamp, ext)
}

// IsValidFilename validates filename against OS restrictions
func IsValidFilename(filename string) bool {
	if filename == "" {
		return false
	}
	
	// Check length restrictions (most filesystems support 255 bytes max)
	if len(filename) > 255 {
		return false
	}
	
	// Check for dangerous characters
	dangerousChars := []string{"<", ">", ":", "\"", "|", "?", "*", "\\", "/"}
	for _, char := range dangerousChars {
		if strings.Contains(filename, char) {
			return false
		}
	}
	
	// Check for control characters
	for _, r := range filename {
		if r < 32 || r == 127 { // Control characters
			return false
		}
	}
	
	// Check for Windows reserved names (case-insensitive)
	reservedNames := []string{
		"CON", "PRN", "AUX", "NUL",
		"COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
		"LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
	}
	
	// Extract base name without extension for reserved name check
	baseName := filename
	if dotIndex := strings.LastIndex(filename, "."); dotIndex != -1 {
		baseName = filename[:dotIndex]
	}
	
	upperBaseName := strings.ToUpper(baseName)
	for _, reserved := range reservedNames {
		if upperBaseName == reserved {
			return false
		}
	}
	
	// Check for leading/trailing periods and spaces (problematic on Windows)
	if strings.HasPrefix(filename, ".") || strings.HasSuffix(filename, ".") {
		return false
	}
	if strings.HasPrefix(filename, " ") || strings.HasSuffix(filename, " ") {
		return false
	}
	
	return true
}
