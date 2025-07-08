// Download service with concurrent processing and organization
package downloader

import (
	"fmt"
	"path/filepath"

	"github.com/FarhadManiCodes/gmail-attachment-downloader/internal/config"
	"github.com/FarhadManiCodes/gmail-attachment-downloader/internal/gmail"
	"github.com/FarhadManiCodes/gmail-attachment-downloader/internal/utils"
)

// Service orchestrates attachment downloading with organization
type Service struct {
	gmailClient *gmail.Client
	config      *config.DownloadConfig
}

// Progress tracks download progress for UI feedback
type Progress struct {
	Total       int
	Completed   int
	Failed      int
	CurrentFile string
}

// NewService creates downloader with dependencies injected
func NewService(client *gmail.Client, cfg config.DownloadConfig) *Service {
	return &Service{
		gmailClient: client,
		config:      &cfg,
	}
}

// ProcessMessages downloads all attachments from messages
func (s *Service) ProcessMessages(messages []gmail.Message) error {
	fmt.Printf("📦 Processing %d messages\n", len(messages))
	
	// Ensure download directory exists
	if err := utils.EnsureDirectory(s.config.BaseDir); err != nil {
		return fmt.Errorf("failed to create download directory: %w", err)
	}
	
	// TODO: Implement concurrent processing with worker pool
	// TODO: Apply file filtering and deduplication
	// TODO: Progress reporting via channels
	
	for _, msg := range messages {
		s.processMessage(msg)
	}
	
	return nil
}

// processMessage handles single message with all attachments
func (s *Service) processMessage(msg gmail.Message) error {
	fmt.Printf("📧 %s from %s\n", msg.Subject, msg.From)
	
	for _, att := range msg.Attachments {
		if err := s.downloadAttachment(msg, att); err != nil {
			fmt.Printf("❌ Failed: %s - %v\n", att.Filename, err)
			continue
		}
	}
	
	return nil
}

// downloadAttachment saves single attachment with organization
func (s *Service) downloadAttachment(msg gmail.Message, att gmail.Attachment) error {
	// Smart filename sanitization
	safeFilename := utils.SanitizeFilename(att.Filename)
	
	// Organize by configured strategy
	downloadPath := s.buildDownloadPath(msg, safeFilename)
	
	fmt.Printf("💾 %s (%s) → %s\n", 
		safeFilename, 
		utils.FormatFileSize(att.Size), 
		downloadPath)
	
	// TODO: Download attachment data from Gmail
	// TODO: Write to file with atomic operations
	// TODO: Set file permissions and timestamps
	
	return nil
}

// buildDownloadPath creates organized file path based on strategy
func (s *Service) buildDownloadPath(msg gmail.Message, filename string) string {
	switch s.config.OrganizeBy {
	case "sender":
		senderDir := utils.SanitizeFilename(msg.From)
		return filepath.Join(s.config.BaseDir, senderDir, filename)
	case "date":
		return filepath.Join(s.config.BaseDir, msg.Date, filename)
	case "type":
		ext := filepath.Ext(filename)
		return filepath.Join(s.config.BaseDir, ext, filename)
	default: // flat
		return filepath.Join(s.config.BaseDir, filename)
	}
}
