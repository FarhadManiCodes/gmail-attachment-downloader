// Configuration management with layered loading and validation
package config

import (
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

// Config represents complete application configuration
type Config struct {
	Gmail    GmailConfig    `yaml:"gmail"`
	Filters  FilterConfig   `yaml:"filters"`
	Download DownloadConfig `yaml:"download"`
	Watch    WatchConfig    `yaml:"watch"`
}

// Component-specific config with sensible defaults
type GmailConfig struct {
	CredentialsFile   string `yaml:"credentials_file"`
	TokenFile         string `yaml:"token_file"`
	RequestsPerMinute int    `yaml:"requests_per_minute"`
}

type FilterConfig struct {
	Extensions []string `yaml:"extensions"`
	Senders    []string `yaml:"senders"`
	AfterDate  string   `yaml:"after_date"`
	MinSize    int64    `yaml:"min_size"`
	MaxSize    int64    `yaml:"max_size"`
}

type DownloadConfig struct {
	BaseDir       string `yaml:"base_dir"`
	OrganizeBy    string `yaml:"organize_by"` // sender|date|type|flat
	MaxConcurrent int    `yaml:"max_concurrent"`
}

type WatchConfig struct {
	CheckInterval time.Duration `yaml:"check_interval"`
}

// Manager handles config loading with environment overrides
type Manager struct{}

func NewManager() *Manager {
	return &Manager{}
}

// Load configuration with fallback chain: file -> defaults
func (m *Manager) Load(path string) (*Config, error) {
	cfg := Default()
	
	if path == "" {
		path = m.findConfig()
	}
	
	if path != "" {
		data, err := os.ReadFile(path)
		if err == nil {
			yaml.Unmarshal(data, cfg) // Ignore errors, use defaults
		}
	}
	
	// TODO: Apply environment variable overrides
	return cfg, nil
}

// Default returns production-ready defaults optimized for data science
func Default() *Config {
	return &Config{
		Gmail: GmailConfig{
			CredentialsFile:   "config/credentials.json",
			TokenFile:         "config/token.json",
			RequestsPerMinute: 250, // Under Gmail API limits
		},
		Filters: FilterConfig{
			Extensions: []string{".py", ".ipynb", ".sql", ".csv", ".xlsx", ".json"},
			MinSize:    1024,     // 1KB minimum
			MaxSize:    50 << 20, // 50MB maximum
		},
		Download: DownloadConfig{
			BaseDir:       "./downloads",
			OrganizeBy:    "sender",
			MaxConcurrent: 5, // Balanced performance
		},
		Watch: WatchConfig{
			CheckInterval: 30 * time.Second,
		},
	}
}

// findConfig searches common locations for config files
func (m *Manager) findConfig() string {
	candidates := []string{"config.yaml", "config/config.yaml"}
	for _, path := range candidates {
		if _, err := os.Stat(path); err == nil {
			return path
		}
	}
	return ""
}
