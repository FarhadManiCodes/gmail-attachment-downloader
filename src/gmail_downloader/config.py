"""
Configuration management with YAML support
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class FilterConfig:
    """Email filtering configuration"""
    senders: List[str] = field(default_factory=list)
    extensions: List[str] = field(default_factory=lambda: [".pdf", ".docx", ".xlsx"])
    after_date: Optional[str] = None
    before_date: Optional[str] = None
    min_size: int = 1024
    max_size: int = 50 * 1024 * 1024  # 50MB

@dataclass
class DownloadConfig:
    """Download configuration"""
    base_dir: str = "./downloads"
    organize_by: str = "sender"  # sender, date, flat
    overwrite_existing: bool = False

@dataclass
class GmailConfig:
    """Gmail API configuration"""
    credentials_file: str = "config/credentials.json"
    token_file: str = "config/token.json"

@dataclass
class AppConfig:
    """Main application configuration"""
    gmail: GmailConfig = field(default_factory=GmailConfig)
    filters: FilterConfig = field(default_factory=FilterConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)

def load_config(config_path: str = "config/config.yaml") -> AppConfig:
    """Load configuration from YAML file"""
    
    config_file = Path(config_path)
    
    if not config_file.exists():
        print(f"⚠️ Config file not found: {config_path}")
        print("Using default configuration")
        return AppConfig()
    
    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # TODO: Parse and validate configuration
        print(f"✅ Loaded config from: {config_path}")
        return AppConfig()
        
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        print("Using default configuration")
        return AppConfig()

def save_config(config: AppConfig, config_path: str = "config/config.yaml") -> None:
    """Save configuration to YAML file"""
    # TODO: Implement config saving
    print(f"💾 Saving config to: {config_path}")
