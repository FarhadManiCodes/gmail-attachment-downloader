// Gmail API client with clean interface and error handling
package gmail

import (
	"context"
	"fmt"

	"github.com/FarhadManiCodes/gmail-attachment-downloader/internal/config"
)

// Client wraps Gmail API with application-specific interface
type Client struct {
	config *config.GmailConfig
	ctx    context.Context
	// TODO: Add *gmail.Service when implementing
}

// Domain models - clean separation from API types
type Message struct {
	ID          string
	ThreadID    string
	Subject     string
	From        string
	Date        string
	Attachments []Attachment
}

type Attachment struct {
	ID       string
	Filename string
	MimeType string
	Size     int64
	Data     []byte // Only populated after download
}

type SearchFilters struct {
	Senders    []string
	Extensions []string
	AfterDate  string
	HasAttachment bool
}

// NewClient creates authenticated Gmail client
func NewClient(cfg config.GmailConfig) *Client {
	return &Client{
		config: &cfg,
		ctx:    context.Background(),
	}
}

// Authenticate handles OAuth2 flow with token persistence
func (c *Client) Authenticate() error {
	fmt.Println("🔐 Gmail authentication...")
	// TODO: Implement OAuth2 flow
	// TODO: Load existing token or run browser flow
	// TODO: Save refreshed tokens
	return nil
}

// SearchMessages finds emails matching filters
func (c *Client) SearchMessages(filters SearchFilters) ([]Message, error) {
	fmt.Printf("🔍 Searching with filters: %+v\n", filters)
	// TODO: Build Gmail search query
	// TODO: Execute search with pagination
	// TODO: Convert API response to domain models
	return []Message{}, nil
}

// DownloadAttachment retrieves attachment data
func (c *Client) DownloadAttachment(messageID, attachmentID string) ([]byte, error) {
	fmt.Printf("📥 Downloading attachment %s\n", attachmentID)
	// TODO: Call Gmail API attachments.get
	// TODO: Decode base64url data
	// TODO: Return raw bytes
	return []byte{}, nil
}

// BuildSearchQuery converts filters to Gmail search syntax
func (c *Client) BuildSearchQuery(filters SearchFilters) string {
	// TODO: Implement Gmail search query builder
	// Example: "from:user@example.com has:attachment filename:pdf"
	return "has:attachment"
}
