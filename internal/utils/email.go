// Email utilities with robust validation and parsing
package utils

import (
	"regexp"
	"strings"
)

// Basic but effective email validation
var emailRegex = regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)

// IsValidEmail validates email format
func IsValidEmail(email string) bool {
	email = strings.TrimSpace(email)
	return len(email) > 0 && emailRegex.MatchString(email)
}

// ExtractEmail handles "Name <email>" and plain email formats
func ExtractEmail(input string) string {
	input = strings.TrimSpace(input)
	
	// Handle "Name <email@domain.com>" format
	if start := strings.Index(input, "<"); start != -1 {
		if end := strings.Index(input[start:], ">"); end != -1 {
			return strings.TrimSpace(input[start+1 : start+end])
		}
	}
	
	return input
}
