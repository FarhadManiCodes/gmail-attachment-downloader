# Gmail Attachment Downloader

Automatically download Gmail attachments with real-time monitoring and smart organization.

## Features

- 🔄 **Real-time monitoring** - Watch for new emails and download attachments instantly
- 📧 **Smart filtering** - Filter by sender, date range, and file types
- 📁 **Auto-organization** - Organize downloads by sender, date, or custom structure  
- 🚀 **Modern CLI** - Beautiful terminal interface with progress tracking
- ⚡ **Fast & efficient** - Async operations for better performance
- 🔒 **Secure** - OAuth2 authentication with Google

## Quick Start

1. **Install**
   ```bash
   pip install -e .
   ```

2. **Setup Google API credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Download as `config/credentials.json`

3. **Run**
   ```bash
   # Download all attachments from a specific sender
   gmail-downloader download --sender "important@company.com"
   
   # Watch mode - monitor for new emails in real-time
   gmail-downloader watch --sender "interviews@company.com"
   ```

## Usage

### Download Mode
```bash
# Download from specific sender
gmail-downloader download --sender "reports@company.com"

# Filter by date and file type
gmail-downloader download --after "2024-01-01" --extensions .pdf .xlsx

# Custom output directory
gmail-downloader download --output "/path/to/downloads"
```

### Watch Mode (Real-time monitoring)
```bash
# Monitor specific sender
gmail-downloader watch --sender "interviewer@company.com"

# Monitor multiple senders with custom filters
gmail-downloader watch --sender "hr@company.com" --sender "manager@company.com" --extensions .pdf
```

## Configuration

Edit `config/config.yaml` to customize default settings:

```yaml
filters:
  senders: ["important@company.com"]
  extensions: [".pdf", ".docx", ".xlsx"]
  
download:
  base_dir: "./downloads"
  organize_by: "sender"  # sender, date, flat
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/
ruff check src/ tests/
```
