// Application layer - orchestrates business logic with clean interfaces
package app

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/FarhadManiCodes/gmail-attachment-downloader/internal/config"
	"github.com/FarhadManiCodes/gmail-attachment-downloader/internal/gmail"
	"github.com/FarhadManiCodes/gmail-attachment-downloader/internal/downloader"
)

// App coordinates all components with clean dependency injection
type App struct {
	config     *config.Manager
	gmailClient *gmail.Client
	downloader  *downloader.Service
}

// New creates application with all dependencies wired up
func New() *App {
	// Clean initialization order with error handling
	configMgr := config.NewManager()
	cfg, err := configMgr.Load("")
	if err != nil {
		fmt.Printf("⚠️  Using default config: %v\n", err)
		cfg = config.Default()
	}

	// Dependency injection pattern
	gmailClient := gmail.NewClient(cfg.Gmail)
	downloaderSvc := downloader.NewService(gmailClient, cfg.Download)

	return &App{
		config:      configMgr,
		gmailClient: gmailClient,
		downloader:  downloaderSvc,
	}
}

// Command builders - clean separation of CLI and business logic
func (a *App) DownloadCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "download",
		Short: "Download attachments matching filters",
		RunE:  a.runDownload,
	}
	
	// CLI flags with sensible defaults
	cmd.Flags().StringSlice("sender", []string{}, "Filter by sender emails")
	cmd.Flags().StringSlice("ext", []string{}, "File extensions (.py,.sql,.csv)")
	cmd.Flags().String("after", "", "Date filter (YYYY-MM-DD)")
	cmd.Flags().String("output", "", "Output directory")
	
	return cmd
}

func (a *App) WatchCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "watch",
		Short: "Monitor Gmail for new attachments",
		RunE:  a.runWatch,
	}
}

func (a *App) ConfigCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "config",
		Short: "Manage configuration",
		RunE:  a.runConfig,
	}
}

// Business logic handlers - clean and focused
func (a *App) runDownload(cmd *cobra.Command, args []string) error {
	fmt.Println("🔍 Searching Gmail for attachments...")
	
	// TODO: Build filters from CLI flags
	// TODO: Search messages with gmail client
	// TODO: Process downloads with downloader service
	
	fmt.Println("✅ Download complete")
	return nil
}

func (a *App) runWatch(cmd *cobra.Command, args []string) error {
	fmt.Println("👁️  Starting real-time monitoring...")
	// TODO: Implement watch loop with channels
	return nil
}

func (a *App) runConfig(cmd *cobra.Command, args []string) error {
	cfg, _ := a.config.Load("")
	fmt.Printf("📁 Base directory: %s\n", cfg.Download.BaseDir)
	fmt.Printf("🎯 Default extensions: %v\n", cfg.Filters.Extensions)
	return nil
}
