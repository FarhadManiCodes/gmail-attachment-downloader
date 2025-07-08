// Integration test to verify component wiring
package test

import (
	"testing"

	"github.com/FarhadManiCodes/gmail-attachment-downloader/internal/app"
	"github.com/FarhadManiCodes/gmail-attachment-downloader/internal/config"
	"github.com/FarhadManiCodes/gmail-attachment-downloader/internal/utils"
)

func TestAppCreation(t *testing.T) {
	// Test clean dependency injection
	app := app.New()
	if app == nil {
		t.Fatal("App creation failed")
	}
}

func TestConfigLoading(t *testing.T) {
	mgr := config.NewManager()
	cfg, err := mgr.Load("")
	if err != nil {
		t.Fatalf("Config loading failed: %v", err)
	}
	
	if len(cfg.Filters.Extensions) == 0 {
		t.Error("Default extensions not loaded")
	}
}

func TestUtilities(t *testing.T) {
	// Test essential utilities
	if !utils.IsValidEmail("test@example.com") {
		t.Error("Email validation failed")
	}
	
	if utils.SanitizeFilename("bad<file>.txt") == "bad<file>.txt" {
		t.Error("Filename sanitization failed")
	}
}
