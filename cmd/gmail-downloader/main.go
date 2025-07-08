// Gmail Attachment Downloader - Production CLI for data science workflows
package main

import (
	"log"
	"os"

	"github.com/spf13/cobra"
	"github.com/FarhadManiCodes/gmail-attachment-downloader/internal/app"
)

var rootCmd = &cobra.Command{
	Use:   "gmail-downloader",
	Short: "Fast Gmail attachment downloader for data science workflows",
	Long: `Download attachments from Gmail with advanced filtering:
  • Data science focus (.py, .ipynb, .sql, .csv, .xlsx)
  • Real-time monitoring with configurable intervals  
  • Smart organization by sender, date, or file type
  • Concurrent downloads with rate limiting`,
}

func main() {
	// Clean dependency injection - app handles all business logic
	application := app.New()
	
	// Wire up commands with clean separation
	rootCmd.AddCommand(application.DownloadCommand())
	rootCmd.AddCommand(application.WatchCommand())
	rootCmd.AddCommand(application.ConfigCommand())
	
	if err := rootCmd.Execute(); err != nil {
		log.Fatal(err)
	}
}
