// File utilities with cross-platform safety and edge case handling
package utils

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

// SanitizeFilename creates safe filename for all platforms
func SanitizeFilename(filename string) string {
	if filename == "" {
		return "unnamed"
	}
	
	// Remove/replace dangerous characters for cross-platform safety
	dangerous := regexp.MustCompile(`[<>:"|?*\\/]`)
	safe := dangerous.ReplaceAllString(filename, "_")
	
	// Handle control characters and Unicode issues
	safe = strings.Map(func(r rune) rune {
		if r < 32 || r == 127 { // Control characters
			return '_'
		}
		return r
	}, safe)
	
	// Clean up and validate result
	safe = strings.Trim(safe, " .")
	if safe == "" {
		safe = "unnamed"
	}
	
	return safe
}

// EnsureDirectory creates directory path with proper permissions
func EnsureDirectory(path string) error {
	if path == "" {
		return fmt.Errorf("empty path")
	}
	
	absPath, err := filepath.Abs(path)
	if err != nil {
		return fmt.Errorf("invalid path: %w", err)
	}
	
	return os.MkdirAll(absPath, 0755)
}

// FormatFileSize returns human-readable size with appropriate units
func FormatFileSize(bytes int64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	
	units := []string{"B", "KB", "MB", "GB", "TB"}
	size := float64(bytes)
	i := 0
	
	for size >= unit && i < len(units)-1 {
		size /= unit
		i++
	}
	
	// Smart precision based on size
	if size >= 100 {
		return fmt.Sprintf("%.0f %s", size, units[i])
	}
	return fmt.Sprintf("%.1f %s", size, units[i])
}
